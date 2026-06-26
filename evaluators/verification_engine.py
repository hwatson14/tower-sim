"""
evaluators/verification_engine.py -- Verification verdict and EP oracle loading.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Callable

import pandas as pd

from qe.contracts import compat_surface_from_legacy_canonical as _state


def _parse_ep_value(raw):
    if raw is None:
        return None, None
    s = str(raw).strip()
    if not s or s.lower() == 'nan':
        return None, None
    if s.startswith('x'):
        try:
            return float(s[1:]), 'multiplier_display'
        except ValueError:
            return None, None
    suffixes = {'K': 1e3, 'M': 1e6, 'B': 1e9, 'T': 1e12, 'q': 1e15, 'Q': 1e18, 'O': 1e27}
    m = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)\s*([KMBTqQO])', s)
    if m:
        return float(m.group(1)) * suffixes[m.group(2)], 'scaled_number'
    try:
        return float(s), 'number'
    except ValueError:
        return None, None


EP_NONCOMPARABLE_DESTINATIONS = {
    _state('free_attack_upgrade_chance_pct'),
    _state('free_defense_upgrade_chance_pct'),
    _state('free_utility_upgrade_chance_pct'),
}

EP_LABEL_TO_DESTINATION = {
    'Attack Speed': _state('tower_attack_speed'),
    'Critical Chance': _state('tower_crit_chance_pct'),
    'Critical Factor': _state('tower_crit_multiplier'),
    'Range': _state('tower_range_m'),
    'Damage / Meter': _state('tower_damage_per_meter_multiplier'),
    'Multishot Chance': _state('tower_multishot_chance_pct'),
    'Multishot Targets': _state('tower_multishot_targets'),
    'Rapid Fire Chance': _state('tower_rapid_fire_chance_pct'),
    'Rapid Fire Duration': _state('tower_rapid_fire_duration_seconds'),
    'Bounce Shot Chance': _state('tower_bounce_shot_chance_pct'),
    'Bounce Shot Targets': _state('tower_bounce_shot_targets'),
    'Super Crit Chance': _state('tower_supercrit_chance_pct'),
    'Super Crit Multiplier': _state('tower_supercrit_multiplier'),
    'Recovery Package Chance': _state('package_chance_pct'),
    'Health': _state('tower_hp'),
    'Health Regen': _state('tower_regen'),
    'Defense Absolute': _state('tower_defense_absolute'),
    'Defense %': _state('tower_defense_pct'),
    'Wall Health': _state('wall_hp'),
    'Wall Fortification': 'derived::wall.hp_final',
    'Wall Regen': _state('wall_regen'),
    'Max Recovery': _state('max_recovery_multiplier'),
    'Coins / Kill Bonus': _state('coins_per_kill_bonus'),
    'Free Attack Upgrade': _state('free_attack_upgrade_chance_pct'),
    'Free Defense Upgrade': _state('free_defense_upgrade_chance_pct'),
    'Free Utility Upgrade': _state('free_utility_upgrade_chance_pct'),
    'Damage': _state('tower_damage'),
}


def verdict_from_verification(verification_status: str, compare_status: str | None) -> str:
    if verification_status == 'not_applicable':
        return 'pass'
    if verification_status in {'not_resolved', 'blocked', 'needs_work'}:
        return 'fail' if verification_status in {'not_resolved', 'blocked'} else 'needs_work'
    if verification_status == 'trace_only':
        return 'trace_only'
    if compare_status in {'stage_scope_mismatch', 'formula_blocked', 'not_comparable'}:
        return 'pass_with_compare_limitations'
    return 'pass'


def _load_ep_oracle(ep_path: Path):
    if not ep_path.exists():
        return {}
    df = pd.read_csv(ep_path, header=None)
    out = {}
    for _, row in df.iterrows():
        if len(row) < 4:
            continue
        label = str(row.iloc[2]).strip()
        value_raw = row.iloc[3] if len(row) > 3 else None
        if label in EP_LABEL_TO_DESTINATION:
            parsed, kind = _parse_ep_value(value_raw)
            if parsed is not None:
                out[EP_LABEL_TO_DESTINATION[label]] = {
                    'label': label,
                    'ep_value_raw': value_raw,
                    'ep_value_parsed': parsed,
                    'ep_value_type': kind,
                }
    return out


def _load_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def build_line_by_line_verification(statbook_dict, ep_compare, formula_ledger, formula_contract: Callable[[dict, str], dict]):
    from evaluators.compare_core import kb_alignment_status_from_compare_status
    from evaluators.verification_engine import verdict_from_verification
    verification = {}
    rows = statbook_dict['rows']
    for key, row in rows.items():
        contributors = row.get('contributors', [])
        schema = row.get('schema') or {}
        contract = formula_contract(formula_ledger, key)
        allowed = set(schema.get('allowed_input_value_types') or [])
        allowed_formula_inputs = contract.get('allowed_formula_input_value_types') or []
        if isinstance(allowed_formula_inputs, str):
            allowed_formula_inputs = [allowed_formula_inputs]
        allowed_formula_input_value_types = {str(value) for value in allowed_formula_inputs}
        level_formula_input_allowed = (
            'level' in allowed_formula_input_value_types
            or contract.get('allow_level_contributors') is True
        )
        issues = []
        unresolved = []
        level_rows = []
        semantic_mismatch = []
        level_surface = schema.get('unit') == 'level' or key.endswith('.level') or key.endswith('_level')
        raw_text_surface = 'raw_text' in set(schema.get('expected_input_semantics') or [])
        for c in contributors:
            vt = c.get('value_type')
            notes = str(c.get('notes') or '').lower()
            defaulted_if_missing = c.get('defaulted_if_missing') is True
            if vt == 'level' and not level_surface and not level_formula_input_allowed:
                level_rows.append(c.get('source_name') or c.get('stat_name'))
            if (
                not defaulted_if_missing
                and (
                    c.get('value') is None
                    or 'unresolved' in notes
                    or vt in {'missing_inventory', 'display_token'}
                    or (vt == 'raw_text' and not raw_text_surface)
                )
            ):
                unresolved.append(c.get('source_name') or c.get('stat_name'))
            if allowed and vt is not None and vt not in allowed and vt not in allowed_formula_input_value_types:
                semantic_mismatch.append({
                    'source': c.get('source_name') or c.get('stat_name'),
                    'value_type': vt,
                })
        if level_rows:
            issues.append('level_contributor_present')
        if unresolved:
            issues.append('unresolved_contributor_present')
        if semantic_mismatch:
            issues.append('semantically_incompatible_contributor_present')
        consumed_contributors = None
        notes_text = str(row.get('notes') or '')
        match = re.search(r'Consumed\s+(\d+)\/(\d+)\s+contributors', notes_text)
        if match:
            consumed_contributors = {'consumed': int(match.group(1)), 'listed': int(match.group(2))}
            if int(match.group(1)) < int(match.group(2)):
                issues.append('unconsumed_contributor_present')
        compare = ep_compare.get(key)
        compare_status = None if compare is None else compare.get('status')
        if compare_status == 'mismatch':
            issues.append('ep_reference_mismatch')
        verification_status = 'publishable'
        publish_policy = str(contract.get('publish_policy') or '').strip()
        row_status = row.get('status')
        if key.startswith('raw::'):
            verification_status = 'trace_only'
        elif (
            row_status == 'gated_off'
            or (
                row_status == 'mapped_not_resolved'
                and key.startswith('state::bot.plus.')
                and key.endswith('.unlocked')
            )
        ) and publish_policy == 'allow_if_resolved':
            verification_status = 'not_applicable'
        elif row_status not in {'resolved', 'partially_resolved'} or row.get('final_value') is None:
            verification_status = 'not_resolved'
        if issues:
            if key.startswith('raw::'):
                verification_status = 'trace_only'
            elif verification_status == 'not_applicable':
                verification_status = 'not_applicable'
            else:
                verification_status = 'blocked' if row_status in {'resolved', 'partially_resolved'} else 'needs_work'
        kb_alignment_status = kb_alignment_status_from_compare_status(compare_status)
        verdict = verdict_from_verification(verification_status, compare_status)
        verification[key] = {
            'destination': key,
            'status': row.get('status'),
            'verification_status': verification_status,
            'kb_alignment_status': kb_alignment_status,
            'verdict': verdict,
            'final_value': row.get('final_value'),
            'unit': schema.get('unit'),
            'resolver': schema.get('resolver'),
            'contributor_count': len(contributors),
            'issues': issues,
            'level_contributors': level_rows,
            'unresolved_contributors': unresolved,
            'semantic_mismatches': semantic_mismatch,
            'ep_compare_status': compare_status,
            'ep_compare_delta': None if compare is None else compare.get('delta'),
            'ep_compare_value': None if compare is None else compare.get('package_value'),
            'ep_compare_value_type': None if compare is None else compare.get('package_value_type'),
            'ep_reference_value': None if compare is None else compare.get('ep_value'),
            'ep_reference_value_type': None if compare is None else compare.get('ep_value_type'),
            'compare_context': None if compare is None else {
                'compare_preset': compare.get('compare_preset'),
                'compare_perk_state': compare.get('compare_perk_state'),
                'package_value_source_preset': compare.get('package_value_source_preset'),
                'package_value_source_state_mode': compare.get('package_value_source_state_mode'),
                'ep_stage_context': compare.get('ep_stage_context'),
            },
            'formula_contract': contract,
            'contributor_consumption': consumed_contributors,
        }
    return verification
