"""
evaluators/compare_core.py -- Core comparison logic.
"""
from __future__ import annotations

import copy
import math
import re
import yaml
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from qe.routing import QEResolutionPlanner
from qe.contracts import (
    CANONICAL_PRESET_NAMES,
    COMPAT_LEGACY_RUNTIME_ONLY_PREFIXES,
    normalize_surface_id_to_contract,
    compat_surface_from_legacy_canonical,
    sanitize_perk_presets_for_canonical_output,
    sanitize_preset_name_for_canonical_output,
)


@dataclass(frozen=True)
class PreparedCompareRowsBundle:
    account_state: object
    compare_rows_by_preset: dict
    compare_publishable_rows_by_preset: dict
    package_stage_context: dict


# Planner contract note: compare payloads are prepared upstream via
# QEResolutionPlanner.resolve_report_snapshot(...).


def _sid(surface_id: str) -> str:
    return normalize_surface_id_to_contract(surface_id)


def _state(destination_id: str) -> str:
    return compat_surface_from_legacy_canonical(destination_id)


def _slug_text(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')


def resolve_perk_effect_destination(
    target_stat_id: str,
    *,
    canon_stats: dict,
    alias_index: dict,
    perk_target_destination_overrides: dict,
) -> tuple[str | None, str | None, bool]:
    if target_stat_id in perk_target_destination_overrides:
        destination_object_type, destination_id = perk_target_destination_overrides[target_stat_id]
        return destination_object_type, destination_id, False
    if target_stat_id in canon_stats:
        return 'canonical_stat', target_stat_id, False
    alias_slug = _slug_text(target_stat_id.replace('_', ' '))
    alias_match = alias_index.get(alias_slug)
    if alias_match is None:
        return None, None, False
    destination_object_type, destination_id = alias_match
    return destination_object_type, destination_id, True


def _normalize_row_keyed_payload(rows: dict) -> dict:
    normalized: dict = {}
    for surface_id, row in (rows or {}).items():
        normalized[_sid(str(surface_id))] = row
    return normalized


def kb_alignment_status_from_compare_status(compare_status: str | None) -> str:
    if compare_status in {None, 'not_in_ep'}:
        return 'not_ep_compared'
    if compare_status in {'match', 'close', 'matched_exact', 'matched_close'}:
        return 'aligned'
    if compare_status in {
        'stage_scope_mismatch',
        'formula_blocked',
        'not_comparable',
        'non_comparable',
        'non_numeric_compare',
    }:
        return 'not_comparable'
    return 'misaligned'


_EP_KNOWN_EXPORT_DEFECT_NOTE_PREFIXES = ('ep_export_bug:', 'ep_export_drift:')


def _compare_notes_have_known_export_defect(notes: list | tuple | set | None) -> bool:
    return any(
        str(note).startswith(_EP_KNOWN_EXPORT_DEFECT_NOTE_PREFIXES)
        for note in (notes or [])
    )


def _compare_has_known_export_defect(payload: dict) -> bool:
    return (
        payload.get('ep_compare_known_export_defect') is True
        or _compare_notes_have_known_export_defect(payload.get('compare_notes'))
        or _compare_notes_have_known_export_defect(payload.get('notes'))
    )


def _normalize_perk_state(perk_state: str) -> str:
    value = str(perk_state or 'auto').strip().lower()
    if value not in {'auto', 'on', 'off'}:
        raise ValueError(f'Unsupported perk state: {perk_state}')
    return value


def _perks_enabled_for_state(active_perk_preset: str | None, perk_state: str) -> bool:
    normalized = _normalize_perk_state(perk_state)
    if normalized == 'on':
        return True
    if normalized == 'off':
        return False
    return bool(active_perk_preset)


def classify_compare_status(destination: str, contract: dict, package_row, ep_entry: dict, stage_context: dict | None = None, normalize_compare_values: Callable[[str, str, object, object], tuple[object, object, list[str]]] | None = None):
    compare_policy = contract.get('compare_policy', 'normal')
    stage_context = stage_context or {}
    if compare_policy == 'noncomparable':
        return 'non_comparable', None, None, ['formula_ledger_marked_noncomparable']
    if package_row is None:
        return 'missing_from_package', None, None, []
    package_value = package_row.get('final_value')
    ep_value = ep_entry.get('ep_value_parsed')
    if normalize_compare_values is None:
        pkg_cmp, ep_cmp, notes = package_value, ep_value, []
    else:
        pkg_cmp, ep_cmp, notes = normalize_compare_values(destination, compare_policy, package_value, ep_value)
    delta = None
    rel_pct = None
    try:
        if pkg_cmp is not None and ep_cmp is not None:
            delta = float(pkg_cmp) - float(ep_cmp)
            if float(ep_cmp) != 0:
                rel_pct = 100.0 * delta / float(ep_cmp)
    except Exception:
        return 'non_numeric_compare', None, None, notes + ['numeric_comparison_failed']
    if compare_policy == 'scaled_number_noncomparable' and ep_entry.get('ep_value_type') == 'scaled_number':
        return 'non_numeric_compare', delta, rel_pct, notes + ['scaled_ep_surface_noncomparable']
    if delta is not None and abs(delta) < 1e-9:
        return 'matched_exact', delta, rel_pct, notes
    if delta is not None and (abs(delta) < 1e-3 or (rel_pct is not None and abs(rel_pct) < 1.0)):
        return 'matched_close', delta, rel_pct, notes
    if stage_context.get('unsupported_facets'):
        return 'stage_scope_mismatch', delta, rel_pct, notes + [
            'ep_compare_uses_unsupported_stage_facets',
            *stage_context.get('unsupported_facets', []),
        ]
    return 'mismatch', delta, rel_pct, notes


def build_ep_compare(ep_oracle, statbook_rows_by_preset, formula_ledger, package_stage_context, *, ep_stage_context_for_destination: Callable[[str, dict], dict], compare_state_key_for_destination: Callable[[str, str], str], contributor_snapshot: Callable[[object], object], apply_projected_runtime_compare_assumptions: Callable[[str, object, dict], tuple[object, list[str]]], formula_contract: Callable[[dict, str], dict], normalize_compare_values: Callable[[str, str, object, object], tuple[object, object, list[str]]]):
    compare = {}
    for dest, ep in ep_oracle.items():
        stage_context = ep_stage_context_for_destination(dest, package_stage_context)
        stage_context['active_cards_by_preset'] = (package_stage_context or {}).get('active_cards_by_preset', {})
        stage_context['active_modules_by_preset'] = (package_stage_context or {}).get('active_modules_by_preset', {})
        stage_context['modules_inventory'] = (package_stage_context or {}).get('modules_inventory', {})
        compare_preset = stage_context['compare_preset']
        compare_state_key = compare_state_key_for_destination(dest, package_stage_context.get('default_compare_preset', 'Farming') if package_stage_context else 'Farming')
        preset_rows = statbook_rows_by_preset.get(compare_state_key, statbook_rows_by_preset.get(compare_preset, {}))
        raw_pkg = preset_rows.get(dest)
        raw_pkg_snapshot = contributor_snapshot(raw_pkg)
        pkg, assumption_notes = apply_projected_runtime_compare_assumptions(dest, raw_pkg, stage_context)
        pkg_snapshot = contributor_snapshot(pkg)
        contract = formula_contract(formula_ledger, dest)
        status, delta, rel_pct, notes = classify_compare_status(dest, contract, pkg, ep, stage_context, normalize_compare_values)
        compare_notes = assumption_notes + notes
        kb_alignment_status = kb_alignment_status_from_compare_status(status)
        compare[dest] = {
            **ep,
            'ep_value': ep.get('ep_value_parsed'),
            'formula_contract': contract,
            'compare_preset': compare_preset,
            'compare_perk_state': stage_context.get('compare_perk_state'),
            'compare_state_key': compare_state_key,
            'ep_stage_context': stage_context,
            'package_value_before_runtime_assumptions': None if raw_pkg is None else raw_pkg.get('final_value'),
            'runtime_compare_assumptions': assumption_notes,
            'package_value': None if pkg is None else pkg.get('final_value'),
            'package_value_type': None if pkg is None else pkg.get('value_type'),
            'package_value_source_preset': compare_preset,
            'package_value_source_state_mode': package_stage_context.get('state_mode') if package_stage_context else None,
            'package_contributors_before_runtime_assumptions': raw_pkg_snapshot,
            'package_contributors': pkg_snapshot,
            'delta': delta,
            'relative_delta_pct': rel_pct,
            'status': status,
            'kb_alignment_status': kb_alignment_status,
            'verdict': 'pass_with_compare_limitations' if kb_alignment_status == 'not_comparable' else ('pass' if kb_alignment_status == 'aligned' else 'fail'),
            'compare_notes': compare_notes,
            'notes': compare_notes,
        }
    return compare


def _normalize_compare_values(destination: str, compare_policy: str, package_value, ep_value):
    pkg = package_value
    ep = ep_value
    notes = []
    if compare_policy == 'normalize_percent_scale' and ep is not None:
        if 0 <= ep <= 2.0:
            ep = ep * 100.0
            notes.append('ep_decimal_fraction_scaled_to_percent_points')
    return pkg, ep, notes


def _build_compare_rows_by_preset(prepared_bundle: PreparedCompareRowsBundle):
    return (
        prepared_bundle.account_state,
        prepared_bundle.compare_rows_by_preset,
        prepared_bundle.compare_publishable_rows_by_preset,
        prepared_bundle.package_stage_context,
    )


# ---------------------------------------------------------------------------
# Constants and helpers migrated from compare.py (T12 shard)
# ---------------------------------------------------------------------------

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


def load_perk_compiler_metadata(
    perk_effects: dict | None = None,
    perk_target_destination_overrides: dict | None = None,
) -> tuple[dict, dict]:
    return perk_effects or {}, perk_target_destination_overrides or {}


def _load_lineage_backed_run_perk_destinations() -> set[str]:
    from qe.query_routing import compiler_routing_indexes

    perk_effects, perk_target_destination_overrides = load_perk_compiler_metadata()
    _, canon_stats, alias_index, _, _ = compiler_routing_indexes()
    destinations: set[str] = set()
    for effects in perk_effects.values():
        for effect in effects:
            if str(effect.get('scope', '')).strip() != 'run':
                continue
            target_stat_id = str(effect.get('target_stat_id', '')).strip()
            if not target_stat_id:
                continue
            destination_object_type, destination_id, _from_alias = resolve_perk_effect_destination(
                target_stat_id,
                canon_stats=canon_stats,
                alias_index=alias_index,
                perk_target_destination_overrides=perk_target_destination_overrides,
            )
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


def _sanitized_active_perk_preset(account_state, canonical_output_preset: str) -> str | None:
    return sanitize_preset_name_for_canonical_output(
        getattr(account_state, 'active_perk_preset', None),
        namespace_class=getattr(account_state, 'perk_preset_namespace_class', 'canonical'),
        fallback_preset_name=canonical_output_preset,
    )


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
    policy = ledger.get('policy') or {}
    surface.setdefault('formula_class', 'unclassified')
    surface.setdefault('publish_policy', policy.get('publish_default', 'allow_if_resolved'))
    surface.setdefault('compare_policy', 'normal')
    surface.setdefault('rationale', '')
    return surface


def _build_publishable_statbook(statbook_dict: dict, formula_ledger: dict) -> dict:
    out = copy.deepcopy(statbook_dict)
    rows = out.get('rows', {})
    for destination, row in rows.items():
        contract = _formula_contract(formula_ledger, destination)
        row.setdefault('formula_contract', contract)
        row.setdefault('publishable', True)
        if destination.startswith('raw::'):
            row['publishable'] = False
            row['publish_notes'] = 'Trace-only raw surface.'
            continue
        row_status = row.get('status')
        if row_status not in {'resolved', 'partially_resolved'} or row.get('final_value') is None:
            row['publishable'] = False
            if row_status == 'gated_off' and contract.get('publish_policy') == 'allow_if_resolved':
                row['publish_notes'] = 'Not applicable until an input contributor resolves this optional surface.'
    out.setdefault('diagnostics', {})
    out['diagnostics']['formula_ledger_version'] = formula_ledger.get('version')
    out['diagnostics']['oracle_policy'] = 'forbidden_for_publish'
    return out


def build_compare_status_summary(ep_compare: dict) -> dict:
    status_counts = Counter(v.get('status') for v in ep_compare.values())
    raw_mismatch_count = sum(1 for v in ep_compare.values() if v.get('status') == 'mismatch')
    known_export_defect_count = sum(
        1
        for v in ep_compare.values()
        if v.get('status') == 'mismatch' and _compare_has_known_export_defect(v)
    )
    true_mismatch_count = max(0, raw_mismatch_count - known_export_defect_count)
    stage_scope_rows = {
        destination: payload
        for destination, payload in ep_compare.items()
        if payload.get('status') == 'stage_scope_mismatch'
    }
    stage_scope_facets_by_destination = {
        destination: _stage_scope_unsupported_facets(payload)
        for destination, payload in stage_scope_rows.items()
    }
    unsupported_facet_counts = Counter(
        facet
        for facets in stage_scope_facets_by_destination.values()
        for facet in facets
    )
    user_guess_facet_counts = Counter(
        facet
        for facets in stage_scope_facets_by_destination.values()
        for facet in facets
        if str(facet).startswith('ep_user_guess:')
    )
    shortcut_facet_counts = Counter(
        facet
        for facets in stage_scope_facets_by_destination.values()
        for facet in facets
        if str(facet).startswith('ep_shortcut:')
    )
    unaccounted_stage_scope_destinations = sorted(
        destination
        for destination, facets in stage_scope_facets_by_destination.items()
        if not facets
    )
    matched_count = sum(
        1 for v in ep_compare.values() if v.get('status') in {'matched_exact', 'matched_close'}
    )
    non_comparable_count = sum(1 for v in ep_compare.values() if v.get('status') == 'non_comparable')
    missing_from_package_count = sum(
        1 for v in ep_compare.values() if v.get('status') == 'missing_from_package'
    )
    accounted_stage_scope_count = len(stage_scope_rows) - len(unaccounted_stage_scope_destinations)
    unaccounted_blocking_count = (
        true_mismatch_count
        + non_comparable_count
        + missing_from_package_count
        + len(unaccounted_stage_scope_destinations)
    )
    if unaccounted_blocking_count == 0 and matched_count + accounted_stage_scope_count == len(ep_compare):
        alignment_status = 'aligned_except_accounted_stage_scope_limits'
    elif unaccounted_blocking_count == 0:
        alignment_status = 'no_formula_mismatches_but_compare_scope_incomplete'
    else:
        alignment_status = 'unresolved_ep_alignment_gaps'
    return {
        'ep_compare_count': len(ep_compare),
        'ep_compare_status_counts': dict(sorted(status_counts.items())),
        'ep_mismatch_count': sum(1 for v in ep_compare.values() if v.get('status') not in {'matched_exact', 'matched_close'}),
        'ep_alignment_status': alignment_status,
        'ep_clean_aligned_count': matched_count,
        'ep_accounted_stage_scope_limit_count': accounted_stage_scope_count,
        'ep_unaccounted_alignment_gap_count': unaccounted_blocking_count,
        'ep_raw_formula_mismatch_count': raw_mismatch_count,
        'ep_true_formula_mismatch_count': true_mismatch_count,
        'ep_known_export_defect_count': known_export_defect_count,
        'ep_unknown_formula_mismatch_count': true_mismatch_count,
        'ep_stage_scope_mismatch_count': len(stage_scope_rows),
        'ep_stage_scope_unsupported_facet_counts': dict(sorted(unsupported_facet_counts.items())),
        'ep_stage_scope_user_guess_facet_counts': dict(sorted(user_guess_facet_counts.items())),
        'ep_stage_scope_shortcut_facet_counts': dict(sorted(shortcut_facet_counts.items())),
        'ep_stage_scope_rows_with_accounted_facets': accounted_stage_scope_count,
        'ep_stage_scope_rows_without_accounted_facets': len(unaccounted_stage_scope_destinations),
        'ep_stage_scope_unaccounted_destinations': unaccounted_stage_scope_destinations,
        'ep_non_comparable_count': non_comparable_count,
        'ep_missing_from_package_count': missing_from_package_count,
    }


def _stage_scope_unsupported_facets(payload: dict) -> list[str]:
    notes = [str(note) for note in (payload.get('compare_notes') or [])]
    marker = 'ep_compare_uses_unsupported_stage_facets'
    if marker not in notes:
        return []
    marker_index = notes.index(marker)
    return [
        note
        for note in notes[marker_index + 1:]
        if note and note != marker
    ]


def ensure_compare_authoritative_verdict_fields(compare: dict) -> dict:
    for payload in (compare or {}).values():
        if not isinstance(payload, dict):
            continue
        status = payload.get('status')
        kb_alignment_status = kb_alignment_status_from_compare_status(status)
        payload['kb_alignment_status'] = kb_alignment_status
        payload['verdict'] = (
            'pass_with_compare_limitations'
            if kb_alignment_status == 'not_comparable'
            else ('pass' if kb_alignment_status == 'aligned' else 'fail')
        )
    return compare


def ensure_line_verification_authoritative_verdict_fields(verification: dict) -> dict:
    from evaluators.verification_engine import verdict_from_verification
    for payload in (verification or {}).values():
        if not isinstance(payload, dict):
            continue
        compare_status = payload.get('ep_compare_status')
        payload['kb_alignment_status'] = kb_alignment_status_from_compare_status(compare_status)
        payload['verdict'] = verdict_from_verification(
            payload.get('verification_status'), compare_status
        )
    return verification


def _project_funding_compare_multiplier(stage_context: dict) -> tuple:
    compare_preset = stage_context.get('compare_preset')
    active_modules = (stage_context.get('active_modules_by_preset') or {}).get(compare_preset) or {}
    generator = active_modules.get('generator') or {}
    primary_name = generator.get('primary')
    if primary_name != 'Project Funding':
        return None, None
    assumption = PROJECTED_RUNTIME_COMPARE_CASH_ASSUMPTIONS.get((_state('tower_damage'), 'Project Funding'))
    if not assumption:
        return None, None
    modules_inventory = stage_context.get('modules_inventory') or {}
    module_row = modules_inventory.get('Project Funding') or {}
    rarity = str(module_row.get('rarity') or '').strip()
    rarity_family = None
    for base in ('Ancestral', 'Mythic', 'Legendary', 'Epic'):
        if rarity.startswith(base):
            rarity_family = base
            break
    coeff = PROJECT_FUNDING_RARITY_COEFFICIENTS.get(rarity_family)
    cash = assumption.get('cash')
    if coeff is None or not cash or cash <= 0:
        return None, None
    multiplier = max(1.0, 1.0 + math.log10(float(cash)) * float(coeff))
    note = f"{assumption['note']}__rarity_family_{(rarity_family or 'unknown').lower()}__multiplier_{multiplier:.6f}"
    return multiplier, note


def _apply_projected_runtime_compare_assumptions(destination: str, package_row, stage_context: dict) -> tuple:
    """Apply projected-runtime compare assumption multipliers for cards and Project Funding module."""
    if package_row is None:
        return None, []
    if stage_context.get('package_progression_state') != 'projected_max_progression':
        return package_row, []
    compare_preset = stage_context.get('compare_preset')
    active_cards = set((stage_context.get('active_cards_by_preset') or {}).get(compare_preset) or [])
    adjusted = dict(package_row)
    notes: list[str] = []
    for card_name in active_cards:
        assumption = PROJECTED_RUNTIME_COMPARE_ASSUMPTIONS.get((destination, card_name))
        if not assumption:
            continue
        try:
            adjusted['final_value'] = float(adjusted.get('final_value')) * float(assumption['multiplier'])
            notes.append(assumption['note'])
        except Exception:
            continue
    if destination == _state('tower_damage'):
        try:
            pf_multiplier, pf_note = _project_funding_compare_multiplier(stage_context)
            if pf_multiplier is not None:
                adjusted['final_value'] = float(adjusted.get('final_value')) * float(pf_multiplier)
                notes.append(pf_note)
        except Exception:
            pass
    return adjusted, notes
