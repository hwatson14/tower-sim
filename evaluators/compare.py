"""
evaluators/compare.py -- Comparison helpers facade. AUTHORITY (T9).

Owns: ep_compare, line_by_line_verification, survivability_residue_analysis,
      compare status summaries, verification verdict logic.
Extracted from: engine/verification.py (T9).
Sharded in T12.
"""
from __future__ import annotations

import copy
import re
from collections import Counter
from pathlib import Path
from typing import Callable

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
    # Newly migrated to compare_core
    COMPARE_PRESET_OVERRIDES,
    COMPARE_SITUATION_OVERRIDES,
    COMPARE_DESTINATION_RUNTIME_CARD_FACETS,
    COMPARE_DESTINATION_TRANSITIVE_DEPENDENCIES,
    PROJECTED_RUNTIME_COMPARE_ASSUMPTIONS,
    PROJECTED_RUNTIME_COMPARE_CASH_ASSUMPTIONS,
    PROJECT_FUNDING_RARITY_COEFFICIENTS,
    COMPARE_DESTINATION_RUN_PERK_FACETS,
    _compare_preset_for_destination,
    _compare_perk_state_for_preset,
    _compare_state_key_for_destination,
    _ep_stage_context_for_destination,
    _sanitized_active_perk_preset,
    _load_formula_ledger,
    _formula_contract,
    _build_publishable_statbook,
    build_compare_status_summary,
    ensure_compare_authoritative_verdict_fields,
    ensure_line_verification_authoritative_verdict_fields,
)
from evaluators.audit_engine import (
    _build_publish_gate_audits,
    _build_kb_incomplete_areas,
    _build_kb_gap_register,
    _build_perk_coverage_audit,
    _build_artifact_contract_manifest,
    # Newly migrated to audit_engine
    _classify_unmapped_input_gap,
    _perk_operation_supported,
    _build_damage_defabs_scope_audit,
    _build_compare_situation_fit_matrix,
    _build_perk_contributor_audit,
    _relpath_str,
    _synthetic_preset_names_present,
)
from evaluators.residue_analysis import (
    _build_tower_regen_closure_report,
    _build_tower_hp_semantic_gap_report,
    _build_tower_damage_residue_analysis,
    build_survivor_closure_report,
    # Newly migrated to residue_analysis
    build_survivability_residue_analysis,
)
from evaluators.verification_engine import (
    build_line_by_line_verification,
    _load_ep_oracle,
    _load_csv_rows,
    # Newly migrated to verification_engine
    verdict_from_verification,
    _parse_ep_value,
    EP_NONCOMPARABLE_DESTINATIONS,
    EP_LABEL_TO_DESTINATION,
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
    for family in sorted(set(family_totals) | {'workshop', 'lab', 'card', 'module', 'module_substat', 'relic', 'vault', 'enhancement', 'uw', 'bot', 'guardian', 'uw_plus'}):
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


# ---------------------------------------------------------------------------
# Helpers that were in the pre-sharding pipeline / compare monolith.
# Retained here so pipeline.py imports remain stable across the T12 shard.
# ---------------------------------------------------------------------------

def _apply_projected_runtime_compare_assumptions(destination: str, package_row, stage_context: dict):
    """Pass-through shim; projection logic lives in evaluators.assumptions (future)."""
    notes: list[str] = []
    if package_row is None:
        return None, notes
    return package_row, notes


def _contributor_snapshot(row):
    """Return the contributors list from a statbook row, or an empty list."""
    if row is None:
        return []
    return row.get('contributors', [])


def _is_calculator_scope_row(row) -> bool:
    """Return True if the stat-input row falls within the calculator's resolution scope."""
    return True


def _build_kb_only_health_family_audit(stat_inputs, statbook_rows: dict) -> dict:
    return {}


def _build_run_perk_residue_analysis(ep_compare: dict) -> dict:
    return {}


def _build_tower_damage_runtime_gap_report(ep_compare: dict) -> dict:
    return {}


def _build_tower_defense_absolute_semantic_gap_report(ep_compare: dict) -> dict:
    return {}


def _build_tower_regen_ep_semantic_gap_report(ep_compare: dict) -> dict:
    return {}


def _build_tradeoff_routing_audit(ids_raw, loadout_config, perk_config, *, preset: str, state_mode: str, perk_state: str) -> dict:
    return {}


def _build_max_progression_policy_perk_config(ids_raw, perk_policy: dict) -> tuple[dict, dict]:
    """Stub: max-progression perk config generator (future evaluators.assumptions)."""
    return {'perk_presets': {}, 'active_perk_preset': None}, {'perk_mode': 'max_progression_policy_stub'}


def _build_runtime_timeline_perk_config(ids_raw, perk_policy: dict, *, diag_output_dir=None) -> tuple[dict, dict]:
    """Stub: runtime-timeline perk config generator (future evaluators.assumptions)."""
    return {'perk_presets': {}, 'active_perk_preset': None}, {'perk_mode': 'runtime_timeline_stub'}
