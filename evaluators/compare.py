"""
evaluators/compare.py -- Comparison helpers facade. AUTHORITY (T9).

Owns: ep_compare, line_by_line_verification, survivability_residue_analysis,
      compare status summaries, verification verdict logic.
Extracted from: engine/verification.py (T9).
Sharded in T12.
"""
from __future__ import annotations

import copy
import csv
import math
import re
from collections import Counter
from pathlib import Path
from typing import Callable

import pandas as pd
import yaml

from input.runtime_state import build_runtime_state
from qe.publication import publish_query_surfaces
from qe.routing import QEResolutionPlanner, classify_input_routing
from qe.stat_input_compiler import compile_stat_inputs

from qe.contracts import (
    CANONICAL_PRESET_NAMES,
    COMPAT_LEGACY_RUNTIME_ONLY_PREFIXES,
    compat_surface_from_legacy_canonical,
    normalize_surface_id_to_contract,
    sanitize_perk_presets_for_canonical_output,
    sanitize_preset_name_for_canonical_output,
)

# Re-exports from sharded modules
from evaluators.compare_core import (
    build_ep_compare,
    _build_compare_rows_by_preset,
    classify_compare_status,
    _normalize_compare_values,
    kb_alignment_status_from_compare_status,
    _normalize_perk_state,
    _perks_enabled_for_state,
)
from evaluators.audit_engine import (
    _build_publish_gate_audits,
    _build_kb_incomplete_areas,
    _build_kb_gap_register,
    _build_perk_coverage_audit,
    _build_artifact_contract_manifest,
)
from evaluators.residue_analysis import (
    _build_tower_regen_closure_report,
    _build_tower_hp_semantic_gap_report,
    _build_tower_damage_residue_analysis,
    build_survivor_closure_report,
)
from evaluators.verification_engine import (
    build_line_by_line_verification,
    _load_ep_oracle,
    _load_csv_rows,
)

# Inlined from engine.display (T9: co-located with compare authority)
DISPLAY_SUFFIXES = [
    (1e24, 'S'), (1e21, 's'), (1e18, 'Q'), (1e15, 'q'),
    (1e12, 'T'), (1e9, 'B'), (1e6, 'M'), (1e3, 'k'),
]

_EV_ROOT = Path(__file__).resolve().parents[1]
ROOT = _EV_ROOT

_CAPABILITY_PREFIX = 'state::capability.'

def _sid(surface_id: str) -> str:
    return normalize_surface_id_to_contract(surface_id)


def _state(destination_id: str) -> str:
    return compat_surface_from_legacy_canonical(destination_id)


def _normalize_row_keyed_payload(rows: dict) -> dict:
    normalized: dict = {}
    for surface_id, row in (rows or {}).items():
        normalized[_sid(str(surface_id))] = row
    return normalized

def _trim_decimal_string(text: str) -> str:
    return text.rstrip('0').rstrip('.') if '.' in text else text

def _format_display_number(value) -> str | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    sign = '-' if v < 0 else ''
    av = abs(v)
    for threshold, suffix in DISPLAY_SUFFIXES:
        if av >= threshold:
            scaled = av / threshold
            decimals = 2 if scaled < 10 else (1 if scaled < 100 else 0)
            txt = _trim_decimal_string(f"{scaled:.{decimals}f}")
            return f"{sign}{txt}{suffix}"
    if av == int(av):
        return f"{int(v)}"
    return _trim_decimal_string(f"{v:.3f}")

def _format_display_value(value, value_type: str | None) -> str | None:
    if value is None:
        return None
    vt = value_type or ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if vt in {"pct", "percent_display"}:
        num = _format_display_number(value)
        return f"{num}%" if num is not None else str(value)
    if vt in {"multiplier", "multiplier_display"}:
        num = _format_display_number(value)
        return f"x{num}" if num is not None else f"x{value}"
    return _format_display_number(value) or str(value)


def _annotate_display_fields(statbook_dict: dict) -> None:
    for row in statbook_dict.get('rows', {}).values():
        row['display_value'] = _format_display_value(row.get('final_value'), row.get('value_type'))
        for contributor in row.get('contributors', []):
            contributor['display_value'] = _format_display_value(contributor.get('value'), contributor.get('value_type'))


def verdict_from_verification(verification_status: str, compare_status: str | None) -> str:
    if verification_status in {'not_resolved', 'blocked', 'blocked_formula_pending', 'needs_work'}:
        return 'fail' if verification_status in {'not_resolved', 'blocked', 'blocked_formula_pending'} else 'needs_work'
    if verification_status == 'trace_only':
        return 'trace_only'
    if compare_status in {'stage_scope_mismatch', 'formula_blocked', 'not_comparable'}:
        return 'pass_with_compare_limitations'
    return 'pass'


def build_compare_status_summary(ep_compare: dict) -> dict:
    status_counts = Counter(v.get('status') for v in ep_compare.values())
    return {
        'ep_compare_count': len(ep_compare),
        'ep_compare_status_counts': dict(sorted(status_counts.items())),
        'ep_mismatch_count': sum(1 for v in ep_compare.values() if v.get('status') not in {'matched_exact', 'matched_close'}),
        'ep_true_formula_mismatch_count': sum(1 for v in ep_compare.values() if v.get('status') == 'mismatch'),
        'ep_formula_blocked_count': sum(1 for v in ep_compare.values() if v.get('status') == 'formula_blocked'),
        'ep_stage_scope_mismatch_count': sum(1 for v in ep_compare.values() if v.get('status') == 'stage_scope_mismatch'),
        'ep_non_comparable_count': sum(1 for v in ep_compare.values() if v.get('status') == 'non_comparable'),
        'ep_missing_from_package_count': sum(1 for v in ep_compare.values() if v.get('status') == 'missing_from_package'),
    }


def annotate_compare_display_fields(
    ep_compare: dict,
    format_display_value: Callable[[object, object], str | None] = _format_display_value,
    format_display_number: Callable[[object], str | None] = _format_display_number,
) -> None:
    for payload in ep_compare.values():
        package_value = payload.get('package_value')
        package_value_type = payload.get('package_value_type')
        payload['package_value_display'] = format_display_value(package_value, package_value_type)

        ep_type = payload.get('ep_value_type')
        ep_value = payload.get('ep_value_parsed')
        compare_notes = set(payload.get('compare_notes') or [])
        if ep_value is None:
            payload['ep_value_display'] = None
        elif 'ep_decimal_fraction_scaled_to_percent_points' in compare_notes:
            payload['ep_value_display'] = format_display_value(ep_value * 100.0, 'pct')
        elif ep_type in {'multiplier_display'}:
            payload['ep_value_display'] = format_display_value(ep_value, 'multiplier_display')
        elif ep_type in {'percent_display', 'pct'}:
            payload['ep_value_display'] = format_display_value(ep_value, 'pct')
        else:
            payload['ep_value_display'] = format_display_number(ep_value)

        delta = payload.get('delta')
        if delta is None:
            payload['delta_display'] = None
        elif package_value_type in {'pct', 'percent_display'}:
            payload['delta_display'] = format_display_value(delta, 'pct')
        elif package_value_type in {'multiplier', 'multiplier_display'}:
            payload['delta_display'] = format_display_value(delta, 'multiplier_display')
        else:
            payload['delta_display'] = format_display_number(delta)

        rel = payload.get('relative_delta_pct')
        payload['relative_delta_display'] = (f"{format_display_number(rel)}%" if rel is not None else None)


def ensure_compare_authoritative_verdict_fields(compare: dict) -> dict:
    for payload in (compare or {}).values():
        if not isinstance(payload, dict):
            continue
        status = payload.get('status')
        kb_alignment_status = payload.get('kb_alignment_status')
        if kb_alignment_status is None:
            kb_alignment_status = kb_alignment_status_from_compare_status(status)
            payload['kb_alignment_status'] = kb_alignment_status
        if payload.get('verdict') is None:
            payload['verdict'] = 'pass_with_compare_limitations' if kb_alignment_status == 'not_comparable' else ('pass' if kb_alignment_status == 'aligned' else 'fail'),
    return compare


def ensure_line_verification_authoritative_verdict_fields(verification: dict) -> dict:
    for payload in (verification or {}).values():
        if not isinstance(payload, dict):
            continue
        compare_status = payload.get('ep_compare_status')
        kb_alignment_status = payload.get('kb_alignment_status')
        if kb_alignment_status is None:
            kb_alignment_status = kb_alignment_status_from_compare_status(compare_status)
            payload['kb_alignment_status'] = kb_alignment_status
        if payload.get('verdict') is None:
            payload['verdict'] = verdict_from_verification(payload.get('verification_status'), compare_status)
    return verification


def build_survivability_residue_analysis(ep_compare: dict, compare_situation_fit_matrix: dict, statbook_dict: dict) -> dict:
    destinations = [
        _state('tower_hp'),
        _state('tower_regen'),
        _state('tower_defense_absolute'),
        _state('wall_hp'),
        _state('wall_regen'),
    ]
    best_fit = compare_situation_fit_matrix.get('best_fit_by_destination', {}) if isinstance(compare_situation_fit_matrix, dict) else {}
    analysis = {}
    for dest in destinations:
        compare_row = ep_compare.get(dest, {}) if isinstance(ep_compare, dict) else {}
        fit = best_fit.get(dest, {}) if isinstance(best_fit, dict) else {}
        package_value = compare_row.get('package_value')
        ep_value = compare_row.get('ep_value')
        ratio = None
        if isinstance(package_value, (int, float)) and isinstance(ep_value, (int, float)) and ep_value:
            ratio = package_value / ep_value
        contributor_summary = []
        for c in compare_row.get('package_contributors', []) or []:
            contributor_summary.append({
                'source_family': c.get('source_family'),
                'source_name': c.get('source_name'),
                'preset_name': c.get('preset_name'),
                'value': c.get('value'),
                'value_type': c.get('value_type'),
            })
        analysis[dest] = {
            'status': compare_row.get('status'),
            'package_value': package_value,
            'ep_value': ep_value,
            'relative_delta_pct': compare_row.get('relative_delta_pct'),
            'package_to_ep_ratio': ratio,
            'best_fit_state_key': fit.get('state_key'),
            'best_fit_preset': fit.get('preset'),
            'best_fit_perk_state': fit.get('perk_state'),
            'compare_state_key': compare_row.get('compare_state_key'),
            'compare_preset': compare_row.get('compare_preset'),
            'compare_perk_state': compare_row.get('compare_perk_state'),
            'contributors': contributor_summary,
        }
    tower_hp_ratio = analysis.get(_state('tower_hp'), {}).get('package_to_ep_ratio')
    wall_hp_ratio = analysis.get(_state('wall_hp'), {}).get('package_to_ep_ratio')
    tower_regen_ratio = analysis.get(_state('tower_regen'), {}).get('package_to_ep_ratio')
    wall_regen_ratio = analysis.get(_state('wall_regen'), {}).get('package_to_ep_ratio')
    analysis['_shared_residue_summary'] = {
        'tower_hp_ratio': tower_hp_ratio,
        'wall_hp_ratio': wall_hp_ratio,
        'tower_regen_ratio': tower_regen_ratio,
        'wall_regen_ratio': wall_regen_ratio,
        'tower_hp_vs_wall_hp_ratio_gap': None if tower_hp_ratio is None or wall_hp_ratio is None else wall_hp_ratio - tower_hp_ratio,
        'tower_regen_vs_wall_regen_ratio_gap': None if tower_regen_ratio is None or wall_regen_ratio is None else wall_regen_ratio - tower_regen_ratio,
    }
    return analysis


def _relpath_str(path_like) -> str | None:
    if path_like is None:
        return None
    from qe.contracts import relpath_str
    return relpath_str(path_like)


def _sanitized_account_state_for_output(account_state, canonical_output_preset: str) -> dict:
    payload = account_state.to_dict()
    namespace_class = getattr(account_state, 'perk_preset_namespace_class', 'canonical')
    payload['perk_presets'] = sanitize_perk_presets_for_canonical_output(
        payload.get('perk_presets') or {},
        namespace_class=namespace_class,
        fallback_preset_name=canonical_output_preset,
        active_preset_name=getattr(account_state, 'active_perk_preset', None),
    )
    payload['active_perk_preset'] = sanitize_preset_name_for_canonical_output(
        getattr(account_state, 'active_perk_preset', None),
        namespace_class=namespace_class,
        fallback_preset_name=canonical_output_preset,
    )
    return payload


def _sanitized_configured_perk_presets(account_state, canonical_output_preset: str) -> dict[str, list[str]]:
    raw = {name: [selection.perk_id for selection in selections] for name, selections in account_state.perk_presets.items()}
    return sanitize_perk_presets_for_canonical_output(
        raw,
        namespace_class=getattr(account_state, 'perk_preset_namespace_class', 'canonical'),
        fallback_preset_name=canonical_output_preset,
        active_preset_name=getattr(account_state, 'active_perk_preset', None),
    )


def _sanitized_active_perk_preset(account_state, canonical_output_preset: str) -> str | None:
    return sanitize_preset_name_for_canonical_output(
        getattr(account_state, 'active_perk_preset', None),
        namespace_class=getattr(account_state, 'perk_preset_namespace_class', 'canonical'),
        fallback_preset_name=canonical_output_preset,
    )


def _build_audit_surface_manifest(account_state, canonical_output_preset: str) -> dict:
    card_presets = getattr(account_state, 'card_presets', {}) or {}
    module_presets = getattr(account_state, 'module_presets', {}) or {}
    perk_presets = getattr(account_state, 'perk_presets', {}) or {}
    preset_lane_completeness = {}
    for preset in CANONICAL_PRESET_NAMES:
        preset_lane_completeness[preset] = {
            'cards_explicit': preset in card_presets,
            'cards_empty': preset in card_presets and not bool(card_presets.get(preset)),
            'modules_explicit': preset in module_presets,
            'modules_empty': preset in module_presets and not bool(module_presets.get(preset)),
            'perks_explicit': preset in perk_presets,
            'perks_empty': preset in perk_presets and not bool(perk_presets.get(preset)),
        }
    return {
        'version': 1,
        'canonical_output_preset': canonical_output_preset,
        'surface_contracts': [
            {
                'surface': 'account_state.json',
                'contract': 'full',
                'completeness_scope': 'canonical_full_state',
                'notes': 'canonical account-state snapshot',
            },
            {
                'surface': 'state_matrix.json',
                'contract': 'full',
                'completeness_scope': 'state_mode_resolution_matrix',
                'notes': 'full matrix over supported state modes',
            },
            {
                'surface': 'diagnostics.json',
                'contract': 'partial',
                'completeness_scope': 'selected_context',
                'notes': 'diagnostic/selected-context summaries only',
            },
            {
                'surface': 'statbook_publishable.json',
                'contract': 'partial',
                'completeness_scope': 'publishable_filtered',
                'notes': 'publishable policy filtered rows',
            },
            {
                'surface': 'ep_oracle_compare.json',
                'contract': 'partial',
                'completeness_scope': 'compare_context',
                'notes': 'compare-only selected context',
            },
        ],
        'preset_lane_completeness': preset_lane_completeness,
    }



def _synthetic_preset_names_present(account_state) -> list[str]:
    raw_names = set()
    for lane_map_name in ('card_presets', 'module_presets', 'perk_presets'):
        lane_map = getattr(account_state, lane_map_name, {}) or {}
        raw_names.update(lane_map.keys())
    return sorted(name for name in raw_names if name not in CANONICAL_PRESET_NAMES)


def _build_family_completeness_matrix(account_state, stat_inputs) -> dict:
    from collections import Counter
    family_totals = Counter(row.source_family for row in stat_inputs)
    mapped_totals = Counter(row.source_family for row in stat_inputs if row.destination_id)
    card_presets = getattr(account_state, 'card_presets', {}) or {}
    module_presets = getattr(account_state, 'module_presets', {}) or {}
    perk_presets = getattr(account_state, 'perk_presets', {}) or {}
    preset_lane_completeness = {}
    for preset in CANONICAL_PRESET_NAMES:
        preset_lane_completeness[preset] = {
            'cards_explicit': preset in card_presets,
            'cards_empty': preset in card_presets and not bool(card_presets.get(preset)),
            'modules_explicit': preset in module_presets,
            'modules_empty': preset in module_presets and not bool(module_presets.get(preset)),
            'perks_explicit': preset in perk_presets,
            'perks_empty': preset in perk_presets and not bool(perk_presets.get(preset)),
        }
    families = {}
    for family in sorted(set(family_totals) | {'workshop','lab','card','module','module_substat','relic','vault','enhancement','uw','bot','guardian','uw_plus'}):
        total_rows = int(family_totals.get(family, 0))
        mapped_rows = int(mapped_totals.get(family, 0))
        families[family] = {
            'total_rows': total_rows,
            'mapped_rows': mapped_rows,
            'unmapped_rows': total_rows - mapped_rows,
        }
    return {
        'version': 1,
        'canonical_output_preset': getattr(account_state, 'default_preset', None),
        'canonical_presets': list(CANONICAL_PRESET_NAMES),
        'synthetic_preset_names_present': _synthetic_preset_names_present(account_state),
        'preset_lane_completeness': preset_lane_completeness,
        'families': families,
    }


def _load_formula_ledger(path: Path) -> dict:
    if not path.exists():
        return {'version': 0, 'policy': {}, 'surfaces': {}}
    data = yaml.safe_load(path.read_text()) or {}
    data.setdefault('version', 0)
    data.setdefault('policy', {})
    data.setdefault('surfaces', {})
    return data


def _formula_contract(ledger: dict, destination: str) -> dict:
    surface = dict((ledger.get('surfaces') or {}).get(destination) or {})
    surface.setdefault('formula_class', 'unclassified')
    surface.setdefault('publish_policy', 'allow')
    surface.setdefault('compare_policy', 'normal')
    surface.setdefault('rationale', '')
    return surface


def _build_publishable_statbook(statbook_dict: dict, formula_ledger: dict) -> dict:
    out = copy.deepcopy(statbook_dict)
    rows = out.get('rows', {})
    blocked = []
    for destination, row in rows.items():
        contract = _formula_contract(formula_ledger, destination)
        row.setdefault('formula_contract', contract)
        row.setdefault('publishable', True)
        if destination.startswith('raw::'):
            row['publishable'] = False
            row['publish_notes'] = 'Trace-only raw surface.'
            continue
        if contract.get('publish_policy') == 'block' and row.get('status') == 'resolved':
            row['publishable'] = False
            row['publish_block_reason'] = 'blocked_by_formula_ledger'
            row['status'] = 'blocked_formula_pending'
            note = row.get('notes') or ''
            row['notes'] = (note + ' | ' if note else '') + 'Blocked from publish by destination formula ledger pending exact formula closure.'
            row['final_value'] = None
            blocked.append(destination)
        elif row.get('status') != 'resolved':
            row['publishable'] = False
    out.setdefault('diagnostics', {})['publishable_blocked_destinations'] = blocked
    out['diagnostics']['publishable_blocked_count'] = len(blocked)
    out['diagnostics']['formula_ledger_version'] = formula_ledger.get('version')
    out['diagnostics']['oracle_policy'] = 'forbidden_for_publish'
    return out


# --- compare routing constants and helpers ---
COMPARE_PRESET_OVERRIDES = {
    _state('tower_attack_speed'): 'Tourney',
    _state('tower_crit_chance_pct'): 'Tourney',
    _state('tower_crit_multiplier'): 'Tourney',
    _state('tower_range_m'): 'Tourney',
    _state('tower_damage_per_meter_multiplier'): 'Tourney',
    _state('tower_multishot_chance_pct'): 'Tourney',
    _state('tower_multishot_targets'): 'Tourney',
    _state('tower_rapid_fire_chance_pct'): 'Tourney',
    _state('tower_rapid_fire_duration_seconds'): 'Tourney',
    _state('tower_bounce_shot_chance_pct'): 'Tourney',
    _state('tower_bounce_shot_targets'): 'Tourney',
    _state('tower_supercrit_chance_pct'): 'Tourney',
    _state('tower_supercrit_multiplier'): 'Tourney',
    _state('tower_damage'): 'Tourney',
    _state('package_chance_pct'): 'Tourney',
}

COMPARE_SITUATION_OVERRIDES = {
    _state('tower_damage'): {'preset': 'Tourney', 'perk_state': 'off', 'ep_run_state': 'tournament_perks_off'},
    _state('package_chance_pct'): {'preset': 'Tourney', 'perk_state': 'off', 'ep_run_state': 'tournament_perks_off'},
    _state('tower_hp'): {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
    _state('tower_regen'): {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
    _state('tower_defense_absolute'): {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
    _state('wall_hp'): {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
    _state('wall_regen'): {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
    _state('coin_kill_multiplier'): {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
    _state('coins_per_kill_bonus'): {'preset': 'Farming', 'perk_state': 'on', 'ep_run_state': 'farming_perks_on'},
}

COMPARE_DESTINATION_RUNTIME_CARD_FACETS = {
    _state('tower_damage'): {
        'Berserker': 'conditional_runtime_card__berserker_damage',
    },
}

def _load_lineage_backed_run_perk_destinations() -> set[str]:
    from qe.stat_input_compiler import _load_perk_effects, PERK_TARGET_DESTINATION_OVERRIDES
    from qe.query_routing import compiler_routing_indexes
    def slug_text(text: str) -> str:
        return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')

    perk_effects = _load_perk_effects()
    _, canon_stats, alias_index, _, _ = compiler_routing_indexes()
    destinations: set[str] = set()
    for effects in perk_effects.values():
        for effect in effects:
            if str(effect.get('scope', '')).strip() != 'run':
                continue
            target_stat_id = str(effect.get('target_stat_id', '')).strip()
            if not target_stat_id:
                continue
            destination_object_type = None
            destination_id = None
            if target_stat_id in PERK_TARGET_DESTINATION_OVERRIDES:
                destination_object_type, destination_id = PERK_TARGET_DESTINATION_OVERRIDES[target_stat_id]
            elif target_stat_id in canon_stats:
                destination_object_type, destination_id = 'canonical_stat', target_stat_id
            else:
                alias_slug = slug_text(target_stat_id.replace('_', ' '))
                alias_match = alias_index.get(alias_slug)
                if alias_match is not None:
                    destination_object_type, destination_id = alias_match
            if destination_object_type == 'canonical_stat' and destination_id:
                destinations.add(_state(destination_id))
    return destinations


COMPARE_DESTINATION_RUN_PERK_FACETS = {
    destination: ['run_perks']
    for destination in sorted(_load_lineage_backed_run_perk_destinations())
}

COMPARE_DESTINATION_TRANSITIVE_DEPENDENCIES = {
    _state('wall_hp'): [_state('tower_hp')],
    _state('wall_regen'): [_state('tower_regen')],
}

PROJECTED_RUNTIME_COMPARE_ASSUMPTIONS = {
    (_state('tower_damage'), 'Berserker'): {
        'multiplier': 8.0,
        'note': 'assumed_maxed_berserker_x8_under_max_progression',
    },
}

PROJECTED_RUNTIME_COMPARE_CASH_ASSUMPTIONS = {
    (_state('tower_damage'), 'Project Funding'): {
        'cash': 50_000_000_000.0,
        'note': 'assumed_project_funding_at_cash_50b_under_max_progression',
    },
}

PROJECT_FUNDING_RARITY_COEFFICIENTS = {
    'Epic': 0.125,
    'Legendary': 0.25,
    'Mythic': 0.50,
    'Ancestral': 1.00,
}


def _compare_preset_for_destination(destination: str, default_preset: str = 'Farming') -> str:
    situation = COMPARE_SITUATION_OVERRIDES.get(destination)
    if situation and situation.get('preset'):
        return situation['preset']
    return COMPARE_PRESET_OVERRIDES.get(destination, default_preset)


def _compare_perk_state_for_preset(preset: str, default_perk_state: str, forced_by_preset: dict | None = None, destination: str | None = None) -> str:
    situation = COMPARE_SITUATION_OVERRIDES.get(destination or '')
    if situation and situation.get('perk_state') is not None:
        return _normalize_perk_state(situation['perk_state'])
    forced_by_preset = forced_by_preset or {}
    if preset in forced_by_preset:
        return _normalize_perk_state(forced_by_preset[preset])
    if preset == 'Tourney':
        return 'off'
    return _normalize_perk_state(default_perk_state)



def _compare_state_key_for_destination(destination: str, default_preset: str = 'Farming') -> str:
    situation = COMPARE_SITUATION_OVERRIDES.get(destination)
    if situation:
        preset = situation.get('preset', _compare_preset_for_destination(destination, default_preset))
        perk_state = _normalize_perk_state(situation.get('perk_state', 'auto'))
        return f'{preset}__perks_{perk_state}'
    preset = _compare_preset_for_destination(destination, default_preset)
    return preset

def _ep_stage_context_for_destination(destination: str, package_stage_context: dict | None = None) -> dict:
    package_stage_context = package_stage_context or {}
    preset = _compare_preset_for_destination(destination, package_stage_context.get('default_compare_preset', 'Farming'))
    offense_surface = preset == 'Tourney'

    package_state_mode = package_stage_context.get('state_mode', 'start_of_run')
    perk_materialized_by_preset = package_stage_context.get('perk_materialized_by_preset') or {}
    preset_perk_state = _compare_perk_state_for_preset(preset, package_stage_context.get('perk_state', 'auto'), package_stage_context.get('forced_preset_perk_states', {}), destination)
    perk_support_enabled = bool(perk_materialized_by_preset.get(preset, package_stage_context.get('perk_materialized')))
    active_cards_by_preset = package_stage_context.get('active_cards_by_preset') or {}
    preset_active_cards = set(active_cards_by_preset.get(preset) or [])

    supports_max_progression = package_state_mode == 'max_progression'
    supports_max_workshop = package_state_mode == 'max_progression'
    supports_run_perks = perk_support_enabled

    unsupported_facets = []
    notes = []

    if not supports_max_progression:
        unsupported_facets.append('max_progression')
        notes.append('EP export is max progression rather than the current package progression state.')
    if not supports_max_workshop:
        unsupported_facets.append('max_workshop')
        notes.append('EP export assumes max workshop rather than the current package workshop state.')
    destination_run_perk_facets = list(COMPARE_DESTINATION_RUN_PERK_FACETS.get(destination, []))
    if not offense_surface and not supports_run_perks:
        transitive_dependencies = COMPARE_DESTINATION_TRANSITIVE_DEPENDENCIES.get(destination, [])
        if any(dep in COMPARE_DESTINATION_RUN_PERK_FACETS for dep in transitive_dependencies):
            destination_run_perk_facets.append('run_perks')
        if destination_run_perk_facets:
            unsupported_facets.extend(sorted(set(destination_run_perk_facets)))
            notes.append('EP surface depends on perk-affected stats that are not materialized in the current package run.')

    runtime_card_facets = COMPARE_DESTINATION_RUNTIME_CARD_FACETS.get(destination, {})
    for card_name, facet in runtime_card_facets.items():
        if card_name not in preset_active_cards:
            continue
        assumption = PROJECTED_RUNTIME_COMPARE_ASSUMPTIONS.get((destination, card_name))
        if package_state_mode == 'max_progression' and assumption:
            notes.append(f'Projected compare assumes {card_name} is maxed under max progression using compare-only runtime normalization.')
            continue
        unsupported_facets.append(facet)
        notes.append(f'EP surface may include conditional runtime card state from {card_name}, which is not materialized in the package compare path.')

    if package_state_mode == 'max_progression':
        package_progression_state = 'projected_max_progression'
        package_workshop_state = 'projected_max_workshop'
    else:
        package_progression_state = 'current_ids_snapshot'
        package_workshop_state = 'current_ids_workshop'

    if offense_surface:
        package_run_state = f'{preset.lower()}_perks_off'
    elif supports_run_perks:
        package_run_state = f'{preset.lower()}_perks_on'
    else:
        package_run_state = f'{preset.lower()}_perks_off'

    situation = COMPARE_SITUATION_OVERRIDES.get(destination)
    if situation and situation.get('ep_run_state'):
        ep_run_state = situation['ep_run_state']
    elif preset == 'Tourney':
        ep_run_state = 'tournament_perks_off'
    else:
        ep_run_state = 'farming_or_milestone_perk_state_unspecified' if preset_perk_state == 'auto' else f'{preset.lower()}_perks_{preset_perk_state}'

    return {
        'compare_preset': preset,
        'compare_perk_state': preset_perk_state,
        'ep_progression_state': 'max_progression',
        'ep_workshop_state': 'max_workshop',
        'ep_run_state': ep_run_state,
        'package_progression_state': package_progression_state,
        'package_workshop_state': package_workshop_state,
        'package_run_state': package_run_state,
        'unsupported_facets': unsupported_facets,
        'notes': notes,
    }


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
    suffixes = {'K':1e3,'M':1e6,'B':1e9,'T':1e12,'q':1e15,'Q':1e18,'O':1e27}
    m = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)\s*([KMBTqQO])', s)
    if m:
        return float(m.group(1))*suffixes[m.group(2)], 'scaled_number'
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
        'Wall Fortification': _state('wall_fortification_multiplier'),
        'Wall Regen': _state('wall_regen'),
        'Max Recovery': _state('max_recovery_multiplier'),
        'Coins / Kill Bonus': _state('coins_per_kill_bonus'),
        'Free Attack Upgrade': _state('free_attack_upgrade_chance_pct'),
        'Free Defense Upgrade': _state('free_defense_upgrade_chance_pct'),
        'Free Utility Upgrade': _state('free_utility_upgrade_chance_pct'),
        'Damage': _state('tower_damage'),
}


def _classify_unmapped_input_gap(item):
    source_family = (item.get('source_family') or '').strip().lower()
    stat_name = (item.get('stat_name') or '').strip()
    contributor_id = item.get('contributor_id')

    if contributor_id:
        return 'Calculator wiring / implementation gap'

    runtime_only_patterns = [
        r'Mastery$',
        r'Effect Bans',
        r'Assist Module',
        r'Enemy',
        r'Boss',
        r'Protector',
        r'Ranged',
        r'Fast',
        r'Tank',
        r'Vampire',
        r'Scatter',
        r'Ray',
        r'Resistance',
        r'Ultimate',
        r'Battle Condition',
        r'Card Presets',
        r'Buy Multiplier',
        r'More Round Stats',
        r'Auto Pick',
        r'Ban Perks',
        r'Perk Option Quantity',
        r'First Perk Choice',
        r'Standard Perks Bonus',
        r'Unlock Perks',
        r'END OF ARRAY',
        r'Keys spent',
        r'Total Bonuses',
        r'Misc\.',
        r'Unlocks$',
        r'Discount',
        r'Shards',
        r'Module Coin Cost',
        r'Rare Drop Chance',
        r'Unmerge Module',
        r'Shatter Shards',
    ]
    if any(re.search(pattern, stat_name) for pattern in runtime_only_patterns):
        return 'Intentional non-goal / runtime-only surface'

    if source_family == 'vault' and stat_name in {
        'Attack', 'Defense', 'Utility', 'Cash / Wave', 'Coins / Kill',
        'Coins / Wave', 'Interest / Wave', 'Keys spent', 'Misc.',
        'Total Bonuses', 'Unlocks'
    }:
        return 'Intentional non-goal / runtime-only surface'

    if source_family in {'lab', 'vault'}:
        return 'KB missing executable contract'
    return 'KB missing fact'


def _perk_operation_supported(operation: str) -> bool:
    return operation in {
        'multiplier',
        'remaining_fraction',
        'percentage_points_add',
        'count_add',
        'seconds_add',
        'raw_add',
        'set_to',
        'special_unlock',
        'special_reduction',
    }


def _build_damage_defabs_scope_audit(account_state, stat_inputs, statbook_rows: dict) -> dict:
    surfaces = {
        'tower_damage': {
            'destination_key': _state('tower_damage'),
            'admissible_families': ['workshop', 'lab', 'card', 'module', 'enhancement', 'relic', 'vault'],
        },
        'tower_defense_absolute': {
            'destination_key': _state('tower_defense_absolute'),
            'admissible_families': ['workshop', 'lab', 'module_substat', 'enhancement', 'relic', 'vault'],
        },
    }
    active_preset = account_state.default_preset
    active_cards = set(account_state.card_presets.get(active_preset, []))
    other_presets_with_card = [
        preset for preset, cards in account_state.card_presets.items()
        if preset != active_preset and 'Damage' in cards
    ]
    active_modules = account_state.module_presets.get(active_preset, {})
    active_armor_selection = active_modules.get('armor') if hasattr(active_modules, 'get') else None
    active_armor_modules = []
    for role in ('primary', 'assist'):
        mod_name = getattr(active_armor_selection, role, None) if active_armor_selection is not None else None
        if mod_name:
            mod = account_state.modules_inventory.get(mod_name)
            if mod:
                active_armor_modules.append((role, mod_name, mod))

    def _surface_unmapped_rows(surface_id: str):
        out = []
        for row in stat_inputs:
            if row.destination_id == surface_id and not row.kb_mapped:
                out.append({
                    'source_family': row.source_family,
                    'source_name': row.source_name,
                    'stat_name': row.stat_name,
                    'value': row.value,
                    'value_type': row.value_type,
                    'notes': row.notes,
                })
        return out

    payload = {
        'scope': 'kb_only_damage_defense_absolute_scope_audit',
        'active_preset': active_preset,
        'surfaces': {},
        'findings': [],
    }

    for surface_id, meta in surfaces.items():
        row = statbook_rows.get(meta['destination_key']) or {}
        contributors = row.get('contributors', [])
        contributor_families = sorted({c.get('source_family') for c in contributors if c.get('source_family')})
        contributor_names = sorted({c.get('source_name') for c in contributors if c.get('source_name')})
        payload['surfaces'][surface_id] = {
            'status': row.get('status'),
            'final_value': row.get('final_value'),
            'display_value': row.get('display_value'),
            'admissible_families': meta['admissible_families'],
            'active_contributor_families': contributor_families,
            'active_contributor_names': contributor_names,
            'missing_admissible_families_in_active_preset': [f for f in meta['admissible_families'] if f not in contributor_families],
            'unmapped_rows_bound_to_surface': _surface_unmapped_rows(surface_id),
        }

    damage_inventory = account_state.cards_inventory.get('Damage')
    damage_card_detail = {
        'owned_in_inventory': damage_inventory is not None,
        'inventory_level': damage_inventory.level if damage_inventory is not None else None,
        'active_in_current_preset': 'Damage' in active_cards,
        'other_presets_with_card_active': other_presets_with_card,
    }
    payload['surfaces']['tower_damage']['inactive_admissible_contributors'] = {
        'damage_card': damage_card_detail,
    }

    defense_abs_armor_substats = []
    for role, mod_name, mod in active_armor_modules:
        for sub in mod.substats:
            if (sub.name or '').strip().lower() == 'defense absolute':
                defense_abs_armor_substats.append({
                    'role': role,
                    'module_name': mod_name,
                    'raw_token': sub.raw_token,
                    'display_value': sub.value,
                })
    payload['surfaces']['tower_defense_absolute']['inactive_admissible_contributors'] = {
        'active_armor_module_defense_absolute_substats': defense_abs_armor_substats,
    }

    if damage_inventory is not None and 'Damage' not in active_cards:
        payload['findings'].append({
            'severity': 'medium',
            'surface': 'tower_damage',
            'finding': 'Damage card is owned but not active in the current preset, so card-family damage contribution is legitimately absent from this stat path.',
            'kb_basis': 'kb/cards/tables/card-effect-registry.csv routes DAMAGE base-card effect to tower.damage_multiplier and kb/cards/tables/card-base-ladders.csv provides the ladder.',
            'evidence_in_account': {
                'active_preset': active_preset,
                'damage_card_inventory_level': damage_inventory.level,
                'other_presets_with_card_active': other_presets_with_card,
            },
            'fix_applied': 'No formula patch applied; audit surfaced preset-scoped contributor absence only.',
        })
    elif damage_inventory is None and other_presets_with_card:
        payload['findings'].append({
            'severity': 'high',
            'surface': 'tower_damage',
            'finding': 'Card preset data references Damage in another preset, but cards_inventory has no Damage snapshot. That is an account-state inconsistency worth treating as a parser or source-shape bug until proven otherwise.',
            'kb_basis': 'kb/cards/tables/card-entity-registry.csv and card-base-ladders.csv define DAMAGE as a valid card surface; a preset should not reference a non-existent inventory card silently.',
            'evidence_in_account': {
                'active_preset': active_preset,
                'other_presets_with_card_active': other_presets_with_card,
                'cards_inventory_contains_damage': False,
            },
            'fix_applied': 'No formula patch applied in this iteration; audit surfaced a likely account-state/parser inconsistency.',
        })
    else:
        payload['findings'].append({
            'severity': 'info',
            'surface': 'tower_damage',
            'finding': 'No admissible current-preset contributor family was proven missing from the KB-routed tower_damage path.',
            'kb_basis': 'Active contributors already include workshop, lab, enhancement, relic, vault, and module.',
            'fix_applied': 'None; current mismatch remains unexplained within the active-preset static path.',
        })

    if not defense_abs_armor_substats:
        payload['findings'].append({
            'severity': 'info',
            'surface': 'tower_defense_absolute',
            'finding': 'No active armor-module Defense Absolute substat exists in the current preset, so module-substat contribution is legitimately absent from tower_defense_absolute.',
            'kb_basis': 'kb/modules/tables/module-substats.csv defines Armor -> Defense Absolute as an admissible routed family when present.',
            'evidence_in_account': {
                'active_preset': active_preset,
                'active_armor_modules': [
                    {
                        'role': role,
                        'module_name': mod_name,
                    }
                    for role, mod_name, _ in active_armor_modules
                ],
            },
            'fix_applied': 'No formula patch applied; audit surfaced current-preset contributor absence only.',
        })
    else:
        payload['findings'].append({
            'severity': 'info',
            'surface': 'tower_defense_absolute',
            'finding': 'Active armor module already exposes Defense Absolute substat(s); no missing-family conclusion was warranted.',
            'kb_basis': 'Active armor-module substats include Defense Absolute in the current preset.',
            'fix_applied': 'None.',
        })

    return payload


def _build_compare_situation_fit_matrix(ids_raw, loadout_config, perk_config, formula_ledger, ep_oracle: dict) -> dict:
    states = [
        ('farming__perks_off', 'Farming', 'off', None),
        ('farming__perks_on', 'Farming', 'on', None),
        ('tourney__perks_off', 'Tourney', 'off', None),
        ('tourney__perks_on', 'Tourney', 'on', {'Tourney': 'on'}),
    ]
    views = {}
    best_fit_by_destination = {}
    for state_key, preset, perk_state, forced_preset_perk_states in states:
        _default_state, rows_by_preset, _publishable_rows_by_preset, stage_context = _build_compare_rows_by_preset(
            ids_raw,
            loadout_config,
            perk_config,
            formula_ledger,
            'max_progression',
            preset,
            ep_oracle,
            perk_state,
            forced_preset_perk_states,
        )
        compare = build_ep_compare(ep_oracle, rows_by_preset, formula_ledger, stage_context, ep_stage_context_for_destination=_ep_stage_context_for_destination, compare_state_key_for_destination=_compare_state_key_for_destination, contributor_snapshot=_contributor_snapshot, apply_projected_runtime_compare_assumptions=_apply_projected_runtime_compare_assumptions, formula_contract=_formula_contract, normalize_compare_values=_normalize_compare_values)
        views[state_key] = {
            'preset': preset,
            'perk_state': perk_state,
            **build_compare_status_summary(compare),
        }
        for destination, row in compare.items():
            rel = row.get('relative_delta_pct')
            abs_rel = abs(float(rel)) if rel is not None else float('inf')
            candidate = {
                'state_key': state_key,
                'preset': preset,
                'perk_state': perk_state,
                'status': row.get('status'),
                'package_value': row.get('package_value'),
                'ep_value': row.get('ep_value'),
                'relative_delta_pct': rel,
                'abs_relative_delta_pct': None if rel is None else abs_rel,
            }
            current = best_fit_by_destination.get(destination)
            if current is None or abs_rel < (current.get('abs_relative_delta_pct') if current.get('abs_relative_delta_pct') is not None else float('inf')):
                best_fit_by_destination[destination] = candidate
    best_fit_state_counts = Counter(v['state_key'] for v in best_fit_by_destination.values())
    best_fit_status_counts = Counter(v['status'] for v in best_fit_by_destination.values())
    return {
        'states': views,
        'best_fit_by_destination': dict(sorted(best_fit_by_destination.items())),
        'destination_count': len(best_fit_by_destination),
        'best_fit_state_counts': dict(sorted(best_fit_state_counts.items())),
        'best_fit_status_counts': dict(sorted(best_fit_status_counts.items())),
    }


def _build_perk_contributor_audit(ids_raw, loadout_config, perk_config, state_mode: str, default_preset: str) -> dict:
    destinations_of_interest = {
        _state('tower_damage'),
        _state('tower_hp'),
        _state('tower_regen'),
        _state('tower_defense_absolute'),
        _state('tower_bounce_shot_targets'),
        _state('wall_hp'),
        _state('wall_regen'),
    }
    audit: dict[str, dict] = {}
    for preset_name in ("Farming", "Tourney"):
        account_state = build_runtime_state(
            ids_raw,
            default_preset=default_preset,
            loadout_config=loadout_config,
            perk_config=perk_config,
        )
        stat_inputs = compile_stat_inputs(
            account_state,
            preset_name=preset_name,
            state_mode=state_mode,
            perks_enabled=True,
        )
        for item in stat_inputs:
            if item.source_family != 'perk':
                continue
            destination = f"{item.destination_object_type}::{item.destination_id}"
            if destination not in destinations_of_interest:
                continue
            audit.setdefault(destination, {}).setdefault(preset_name, []).append({
                'perk_name': item.source_name,
                'contributor_id': item.contributor_id,
                'value': item.value,
                'value_type': item.value_type,
                'notes': item.notes,
                'preset_name': item.preset_name,
            })
    for destination_payload in audit.values():
        for rows in destination_payload.values():
            rows.sort(key=lambda r: (r['perk_name'], r['contributor_id']))
    return dict(sorted(audit.items()))
