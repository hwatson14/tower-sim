"""
evaluators/compare_core.py -- Core comparison logic.
"""
from __future__ import annotations

import math
from typing import Callable

from qe.contracts import (
    normalize_surface_id_to_contract,
    compat_surface_from_legacy_canonical,
    sanitize_perk_presets_for_canonical_output,
    sanitize_preset_name_for_canonical_output,
)
from qe.routing import QEResolutionPlanner
from qe.publication import publish_query_surfaces
from input.runtime_state import build_runtime_state


def _sid(surface_id: str) -> str:
    return normalize_surface_id_to_contract(surface_id)


def _state(destination_id: str) -> str:
    return compat_surface_from_legacy_canonical(destination_id)


def _normalize_row_keyed_payload(rows: dict) -> dict:
    normalized: dict = {}
    for surface_id, row in (rows or {}).items():
        normalized[_sid(str(surface_id))] = row
    return normalized


def kb_alignment_status_from_compare_status(compare_status: str | None) -> str:
    if compare_status in {None, 'not_in_ep'}:
        return 'not_ep_compared'
    if compare_status in {'match', 'close'}:
        return 'aligned'
    if compare_status in {'stage_scope_mismatch', 'formula_blocked', 'not_comparable'}:
        return 'not_comparable'
    return 'misaligned'


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
    if contract.get('publish_policy') == 'block':
        return 'formula_blocked', delta, rel_pct, notes + ['known_bad_formula_blocked_from_publish']
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


def _build_compare_rows_by_preset(ids_raw, loadout_config, perk_config, formula_ledger, state_mode: str, default_preset: str, ep_oracle: dict, perk_state: str, forced_preset_perk_states: dict | None = None, snapshot_planner: QEResolutionPlanner | None = None):
    from evaluators.compare import (
        _compare_perk_state_for_preset,
        _compare_state_key_for_destination,
        _formula_contract,
        _build_publishable_statbook,
    )
    from app.display import annotate_display_fields as _annotate_display_fields

    compare_rows_by_preset = {}
    compare_publishable_rows_by_preset = {}

    perk_state_by_preset = {}
    perk_materialized_by_preset = {}
    planner = snapshot_planner or QEResolutionPlanner()
    state_cache = {}
    resolved_cache = {}

    def _state_for_preset(preset_name: str):
        state = state_cache.get(preset_name)
        if state is None:
            state = build_runtime_state(ids_raw, default_preset=preset_name, loadout_config=loadout_config, perk_config=perk_config)
            state_cache[preset_name] = state
        return state

    def _materialize(preset_name: str, forced_perk_state: str | None = None):
        state = _state_for_preset(preset_name)
        preset_perk_state = _normalize_perk_state(forced_perk_state) if forced_perk_state is not None else _compare_perk_state_for_preset(preset_name, perk_state, forced_preset_perk_states)
        perks_enabled = _perks_enabled_for_state(state.active_perk_preset, preset_perk_state)
        state_key = f'{preset_name}__perks_{preset_perk_state}' if forced_perk_state is not None else preset_name
        perk_state_by_preset[state_key] = preset_perk_state
        perk_materialized_by_preset[state_key] = perks_enabled
        request_key = (preset_name, state_mode, bool(perks_enabled))
        resolved = resolved_cache.get(request_key)
        if resolved is None:
            snapshot = planner.resolve_report_snapshot(
                state,
                preset_name=preset_name,
                state_mode=state_mode,
                perks_enabled=perks_enabled,
            )
            statbook = snapshot.statbook
            publish_query_surfaces(statbook.rows, account_state_labs=state.labs)
            statbook_dict = statbook.to_dict()
            for destination, row in statbook_dict.get('rows', {}).items():
                row['formula_contract'] = _formula_contract(formula_ledger, destination)
            _annotate_display_fields(statbook_dict)
            publishable = _build_publishable_statbook(statbook_dict, formula_ledger)
            _annotate_display_fields(publishable)
            resolved = (
                state,
                _normalize_row_keyed_payload(statbook_dict['rows']),
                _normalize_row_keyed_payload(publishable['rows']),
            )
            resolved_cache[request_key] = resolved
        cached_state, cached_rows, cached_publishable_rows = resolved
        state = cached_state
        compare_rows_by_preset[state_key] = cached_rows
        compare_publishable_rows_by_preset[state_key] = cached_publishable_rows
        return state

    default_state = _materialize(default_preset)
    required_state_keys = {_compare_state_key_for_destination(dest, default_preset) for dest in ep_oracle}
    if any(key.startswith('Tourney') for key in required_state_keys):
        if 'Tourney' in required_state_keys:
            _materialize('Tourney')
        if 'Tourney__perks_on' in required_state_keys:
            _materialize('Tourney', forced_perk_state='on')
        if 'Tourney__perks_off' in required_state_keys and 'Tourney' not in required_state_keys:
            _materialize('Tourney', forced_perk_state='off')
    if any(key.startswith('Farming__perks_on') for key in required_state_keys):
        _materialize('Farming', forced_perk_state='on')
    if any(key.startswith('Farming__perks_off') for key in required_state_keys) and default_preset != 'Farming':
        _materialize('Farming', forced_perk_state='off')

    package_stage_context = {
        'state_mode': state_mode,
        'perk_state': _normalize_perk_state(perk_state),
        'perk_materialized': _perks_enabled_for_state(default_state.active_perk_preset, _compare_perk_state_for_preset(default_preset, perk_state, forced_preset_perk_states)),
        'perk_state_by_preset': dict(sorted(perk_state_by_preset.items())),
        'perk_materialized_by_preset': dict(sorted(perk_materialized_by_preset.items())),
        'active_perk_preset': _sanitized_active_perk_preset(default_state, default_preset),
        'default_compare_preset': default_preset,
        'forced_preset_perk_states': dict(sorted((forced_preset_perk_states or {}).items())),
        'active_cards_by_preset': {
            preset_name: list(state.card_presets.get(preset_name, []))
            for preset_name, state in [(default_preset, default_state)]
        },
        'active_modules_by_preset': {
            preset_name: {
                slot: {
                    'primary': selection.primary,
                    'assist': selection.assist,
                }
                for slot, selection in state.module_presets.get(preset_name, {}).items()
            }
            for preset_name, state in [(default_preset, default_state)]
        },
        'modules_inventory': {
            name: {
                'rarity': mod.rarity,
                'level': mod.level,
                'stat': mod.stat,
            }
            for name, mod in default_state.modules_inventory.items()
        },
    }
    for preset_name in compare_rows_by_preset:
        base_preset_name = preset_name.split('__perks_', 1)[0]
        if preset_name == default_preset:
            continue
        state = _state_for_preset(base_preset_name)
        package_stage_context['active_cards_by_preset'][base_preset_name] = list(state.card_presets.get(base_preset_name, []))
        package_stage_context['active_modules_by_preset'][base_preset_name] = {
            slot: {
                'primary': selection.primary,
                'assist': selection.assist,
            }
            for slot, selection in state.module_presets.get(base_preset_name, {}).items()
        }
    return default_state, compare_rows_by_preset, compare_publishable_rows_by_preset, package_stage_context
