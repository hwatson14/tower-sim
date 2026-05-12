"""
evaluators/compare.py -- Comparison helpers. AUTHORITY (T9).

Owns: ep_compare, line_by_line_verification, survivability_residue_analysis,
      compare status summaries, verification verdict logic.
Extracted from: engine/verification.py (T9).
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

from qe.publication import publish_query_surfaces
from qe.routing import classify_input_routing
from evaluators.compare_core import (
    PreparedCompareRowsBundle,
    resolve_perk_effect_destination,
)

from qe.contracts import (
    CANONICAL_PRESET_NAMES,
    COMPAT_LEGACY_RUNTIME_ONLY_PREFIXES,
    compat_surface_from_legacy_canonical,
    normalize_surface_id_to_contract,
    sanitize_perk_presets_for_canonical_output,
    sanitize_preset_name_for_canonical_output,
)

# Inlined from engine.display (T9: co-located with compare authority)
DISPLAY_SUFFIXES = [
    (1e24, 'S'), (1e21, 's'), (1e18, 'Q'), (1e15, 'q'),
    (1e12, 'T'), (1e9, 'B'), (1e6, 'M'), (1e3, 'k'),
]


def _sid(surface_id: str) -> str:
    return normalize_surface_id_to_contract(surface_id)


def _state(destination_id: str) -> str:
    return compat_surface_from_legacy_canonical(destination_id)


def _normalize_row_keyed_payload(rows: dict) -> dict:
    normalized: dict = {}
    for surface_id, row in (rows or {}).items():
        normalized[_sid(str(surface_id))] = row
    return normalized

_CAPABILITY_PREFIX = 'state::capability.'

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


def kb_alignment_status_from_compare_status(compare_status: str | None) -> str:
    if compare_status in {None, 'not_in_ep'}:
        return 'not_ep_compared'
    if compare_status in {'match', 'close'}:
        return 'aligned'
    if compare_status in {'stage_scope_mismatch', 'formula_blocked', 'not_comparable'}:
        return 'not_comparable'
    return 'misaligned'


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


def build_compare_status_summary(ep_compare: dict) -> dict:
    status_counts = Counter(v.get('status') for v in ep_compare.values())
    return {
        'ep_compare_count': len(ep_compare),
        'ep_compare_status_counts': dict(sorted(status_counts.items())),
        'ep_mismatch_count': sum(1 for v in ep_compare.values() if v.get('status') not in {'matched_exact', 'matched_close'}),
        'ep_true_formula_mismatch_count': sum(1 for v in ep_compare.values() if v.get('status') == 'mismatch'),
        'ep_stage_scope_mismatch_count': sum(1 for v in ep_compare.values() if v.get('status') == 'stage_scope_mismatch'),
        'ep_non_comparable_count': sum(1 for v in ep_compare.values() if v.get('status') == 'non_comparable'),
        'ep_missing_from_package_count': sum(1 for v in ep_compare.values() if v.get('status') == 'missing_from_package'),
    }


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
            payload['verdict'] = 'pass_with_compare_limitations' if kb_alignment_status == 'not_comparable' else ('pass' if kb_alignment_status == 'aligned' else 'fail')
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


def build_survivor_closure_report(ep_compare: dict, line_verification: dict) -> dict:
    tracked = [
        _state('tower_regen'),
        _state('tower_hp'),
        _state('tower_defense_absolute'),
        _state('tower_damage'),
        _state('wall_hp'),
        _state('wall_regen'),
    ]
    rows = []
    for destination in tracked:
        verification = dict(line_verification.get(destination) or {})
        compare = dict(ep_compare.get(destination) or {})
        rows.append({
            'destination': destination,
            'verification_status': verification.get('verification_status'),
            'issues': verification.get('issues') or [],
            'final_value': verification.get('final_value'),
            'ep_compare_value': verification.get('ep_compare_value'),
            'ep_reference_value': verification.get('ep_reference_value'),
            'delta': compare.get('delta'),
            'relative_delta_pct': compare.get('relative_delta_pct'),
            'compare_preset': compare.get('compare_preset'),
            'compare_perk_state': compare.get('compare_perk_state'),
            'package_value_source_state_mode': compare.get('package_value_source_state_mode'),
            'ep_stage_context': compare.get('ep_stage_context'),
            'note': (
                'downstream_reflection_of_tower_residue'
        if destination in {_state('wall_hp'), _state('wall_regen')}
                else 'primary_upstream_survivor'
            ),
        })
    return {
        'survivor_order': tracked,
        'rows': rows,
    }


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


def build_line_by_line_verification(statbook_dict, ep_compare, formula_ledger, formula_contract: Callable[[dict, str], dict]):
    verification = {}
    rows = statbook_dict['rows']
    for key, row in rows.items():
        contributors = row.get('contributors', [])
        schema = row.get('schema') or {}
        allowed = set(schema.get('allowed_input_value_types') or [])
        issues = []
        unresolved = []
        level_rows = []
        semantic_mismatch = []
        for c in contributors:
            vt = c.get('value_type')
            notes = str(c.get('notes') or '').lower()
            defaulted_if_missing = c.get('defaulted_if_missing') is True
            if vt == 'level':
                level_rows.append(c.get('source_name') or c.get('stat_name'))
            if (
                not defaulted_if_missing
                and (c.get('value') is None or 'unresolved' in notes or vt in {'missing_inventory', 'raw_text', 'display_token'})
            ):
                unresolved.append(c.get('source_name') or c.get('stat_name'))
            if allowed and vt is not None and vt not in allowed:
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
        contract = formula_contract(formula_ledger, key)
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
        if compare_status == 'stage_scope_mismatch':
            issues.append('ep_reference_stage_scope_mismatch')
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


# ===========================================================================
# T12 migrated domain functions (moved from run_stats.py)
# ===========================================================================

# ---------------------------------------------------------------------------
# path helper (evaluators-local; ROOT = repo root from evaluators/ sub-dir)
# ---------------------------------------------------------------------------
_EV_ROOT = Path(__file__).resolve().parents[1]
ROOT = _EV_ROOT
FORMULA_LEDGER_PATH = ROOT / 'kb' / 'ledgers' / 'formula_surface_policy.yaml'
EP_ORACLE_PATH = ROOT / 'input' / 'imports' / 'ep_export.csv'


def _relpath_str(path_like) -> str | None:
    if path_like is None:
        return None
    p = Path(path_like)
    try:
        return str(p.resolve().relative_to(_EV_ROOT))
    except Exception:
        try:
            return str(p.relative_to(_EV_ROOT))
        except Exception:
            return str(p)


# --- perk state helpers ---
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


# --- account-state sanitizers ---
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


# --- manifest builders ---
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


def _build_artifact_contract_manifest(account_state, canonical_output_preset: str, stat_inputs, statbook_dict: dict) -> dict:
    return {
        'version': 1,
        'canonical_output_preset': canonical_output_preset,
        'canonical_presets': list(CANONICAL_PRESET_NAMES),
        'canonical_preset_count': len(CANONICAL_PRESET_NAMES),
        'synthetic_preset_names_present': _synthetic_preset_names_present(account_state),
        'artifacts': [
            {'surface': 'account_state.json', 'artifact_class': 'canonical_snapshot', 'contract': 'full', 'provenance': 'current_run_generated', 'producer': 'run_stats.py', 'canonical': True},
            {'surface': 'module_card_payloads.json', 'artifact_class': 'ui_payload', 'contract': 'partial', 'provenance': 'qe_generated_from_current_run', 'producer': 'run_stats.py', 'canonical': False},
            {'surface': 'stat_inputs.json', 'artifact_class': 'canonical_snapshot', 'contract': 'full', 'provenance': 'current_run_generated', 'producer': 'run_stats.py', 'canonical': True},
            {'surface': 'statbook.json', 'artifact_class': 'canonical_snapshot', 'contract': 'full', 'provenance': 'current_run_generated', 'producer': 'run_stats.py', 'canonical': True},
            {'surface': 'state_matrix.json', 'artifact_class': 'derived_matrix', 'contract': 'full', 'provenance': 'current_run_generated', 'producer': 'run_stats.py', 'canonical': True},
            {'surface': 'statbook_publishable.json', 'artifact_class': 'publishable_view', 'contract': 'partial', 'provenance': 'policy_filtered_from_current_run', 'producer': 'run_stats.py', 'canonical': False},
            {'surface': 'diagnostics.json', 'artifact_class': 'compare_view', 'contract': 'partial', 'provenance': 'compare_generated_from_current_run_and_ep', 'producer': 'run_stats.py', 'canonical': False},
            {'surface': 'ep_oracle_compare.json', 'artifact_class': 'compare_view', 'contract': 'partial', 'provenance': 'compare_generated_from_current_run_and_ep', 'producer': 'run_stats.py', 'canonical': False},
            {'surface': 'line_by_line_verification.json', 'artifact_class': 'verification_view', 'contract': 'partial', 'provenance': 'verification_generated_from_current_run_and_compare', 'producer': 'run_stats.py', 'canonical': False},
            {'surface': 'survivor_closure_report.json', 'artifact_class': 'verification_view', 'contract': 'partial', 'provenance': 'verification_generated_from_current_run_and_compare', 'producer': 'run_stats.py', 'canonical': False},
            {'surface': 'audit_surface_manifest.json', 'artifact_class': 'audit_manifest', 'contract': 'full', 'provenance': 'manifest_generated_from_current_run', 'producer': 'run_stats.py', 'canonical': True},
            {'surface': 'artifact_contract_manifest.json', 'artifact_class': 'audit_manifest', 'contract': 'full', 'provenance': 'manifest_generated_from_current_run', 'producer': 'run_stats.py', 'canonical': True},
            {'surface': 'family_completeness_matrix.json', 'artifact_class': 'audit_manifest', 'contract': 'full', 'provenance': 'manifest_generated_from_current_run', 'producer': 'run_stats.py', 'canonical': True},
        ],
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


# --- formula ledger helpers ---
def _load_formula_ledger(path: Path) -> dict:
    if not path.exists():
        return {'version': 0, 'policy': {}, 'surfaces': {}}
    data = yaml.safe_load(path.read_text()) or {}
    data.setdefault('version', 0)
    data.setdefault('policy', {})
    data.setdefault('surfaces', {})
    return data


def load_formula_ledger() -> dict:
    """Public evaluator-owned formula-ledger loader for orchestration consumers."""
    return _load_formula_ledger(FORMULA_LEDGER_PATH)


def _formula_contract(ledger: dict, destination: str) -> dict:
    surface = dict((ledger.get('surfaces') or {}).get(destination) or {})
    policy = ledger.get('policy') or {}
    surface.setdefault('formula_class', 'unclassified')
    surface.setdefault('publish_policy', policy.get('publish_default', 'allow_if_resolved'))
    surface.setdefault('compare_policy', 'normal')
    surface.setdefault('rationale', '')
    return surface


def _normalize_compare_values(destination: str, compare_policy: str, package_value, ep_value):
    pkg = package_value
    ep = ep_value
    notes = []
    if compare_policy == 'normalize_percent_scale' and ep is not None:
        if 0 <= ep <= 2.0:
            ep = ep * 100.0
            notes.append('ep_decimal_fraction_scaled_to_percent_points')
    return pkg, ep, notes


def _build_publishable_statbook(statbook_dict: dict, formula_ledger: dict) -> dict:
    from dataclasses import replace
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

def _safe_pct(n: int, d: int) -> float:
    return round((100.0 * n / d), 2) if d else 0.0



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


def _load_perk_compiler_metadata(perk_entities: dict, perk_effects: dict, perk_target_destination_overrides: dict):
    return perk_entities, perk_effects, perk_target_destination_overrides, resolve_perk_effect_destination


def _load_lineage_backed_run_perk_destinations(
    perk_effects: dict | None = None,
    perk_target_destination_overrides: dict | None = None,
) -> set[str]:
    from qe.query_routing import compiler_routing_indexes

    if not perk_effects:
        return set()
    _perk_entities, perk_effects, perk_target_destination_overrides, resolve_destination = _load_perk_compiler_metadata(
        {},
        perk_effects,
        perk_target_destination_overrides or {},
    )
    _, canon_stats, alias_index, _, _ = compiler_routing_indexes()
    destinations: set[str] = set()
    for effects in perk_effects.values():
        for effect in effects:
            if str(effect.get('scope', '')).strip() != 'run':
                continue
            target_stat_id = str(effect.get('target_stat_id', '')).strip()
            if not target_stat_id:
                continue
            destination_object_type, destination_id, _from_alias = resolve_destination(
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
    perk_state_by_preset = package_stage_context.get('perk_state_by_preset') or {}
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


# --- tower regen reports ---
def _build_tower_regen_closure_report(ep_compare: dict) -> dict:
    dest = _state('tower_regen')
    row = (ep_compare or {}).get(dest) or {}
    contributors = row.get('package_contributors') or []
    multiplier_product = 1.0
    workshop_base = None
    ledger = []
    for c in contributors:
        v = c.get('value')
        try:
            vf = float(v)
        except Exception:
            vf = None
        family = c.get('source_family')
        value_type = c.get('value_type')
        factor = None
        if vf is None:
            factor = None
        elif family == 'workshop':
            workshop_base = vf
        elif family == 'module_substat' and value_type == 'percent_display':
            factor = 1.0 + (vf / 100.0)
        elif family == 'enhancement':
            factor = vf
        elif family in {'relic', 'vault'}:
            factor = 1.0 + vf
        elif family in {'lab', 'card', 'perk'}:
            factor = vf if vf > 1.0 else 1.0 + vf
        else:
            factor = vf if vf > 1.0 else 1.0 + vf
        if factor is not None:
            multiplier_product *= factor
        ledger.append({
            'source_family': family,
            'source_name': c.get('source_name'),
            'preset_name': c.get('preset_name'),
            'raw_value': v,
            'value_type': value_type,
            'applied_factor': factor,
        })
    recomputed = None if workshop_base is None else workshop_base * multiplier_product
    ep_value = row.get('ep_value')
    required_missing_multiplier = None
    if isinstance(recomputed, (int, float)) and isinstance(ep_value, (int, float)) and recomputed:
        required_missing_multiplier = ep_value / recomputed
    return {
        'destination': dest,
        'compare_state_key': row.get('compare_state_key'),
        'compare_preset': row.get('compare_preset'),
        'compare_perk_state': row.get('compare_perk_state'),
        'package_value': row.get('package_value'),
        'ep_value': ep_value,
        'relative_delta_pct': row.get('relative_delta_pct'),
        'workshop_base': workshop_base,
        'multiplier_product': multiplier_product,
        'recomputed_package_value': recomputed,
        'required_missing_multiplier_to_match_ep': required_missing_multiplier,
        'contributors': ledger,
    }



def _build_tower_regen_ep_semantic_gap_report(ep_compare: dict) -> dict:
    dest = _state('tower_regen')
    row = (ep_compare or {}).get(dest) or {}
    contributors = row.get('package_contributors') or []

    workshop_base = None
    current_factors = {}
    contributor_meta = {}
    for c in contributors:
        family = c.get('source_family')
        name = c.get('source_name')
        key = f"{family}::{name}"
        value = c.get('value')
        try:
            vf = float(value)
        except Exception:
            vf = None
        factor = None
        if vf is None:
            factor = None
        elif family == 'workshop':
            workshop_base = vf
        elif family == 'module_substat' and c.get('value_type') == 'percent_display':
            factor = 1.0 + (vf / 100.0)
        elif family == 'enhancement':
            factor = vf
        elif family in {'relic', 'vault'}:
            factor = 1.0 + vf
        else:
            factor = vf if vf > 1.0 else 1.0 + vf
        if factor is not None:
            current_factors[key] = factor
        contributor_meta[key] = c

    def _recompute(factors: dict[str, float]) -> float | None:
        if workshop_base is None:
            return None
        out = workshop_base
        for _, factor in factors.items():
            out *= factor
        return out

    ep_value = row.get('ep_value')
    package_value = row.get('package_value')
    package_from_factors = _recompute(current_factors)

    standard_key = 'perk::x1.75 Health Regen'
    tradeoff_key = 'perk::Tower Health Regen x8.00, But Tower Max Max Health -60%'
    enhancement_key = 'enhancement::Health Regen +'

    current_standard = current_factors.get(standard_key)
    current_tradeoff = current_factors.get(tradeoff_key)
    current_enhancement = current_factors.get(enhancement_key)

    ep_standard = None if current_standard is None else (1.0 + 0.75 * 5.0) * (1.0 + 0.01 * 25.0)
    ep_tradeoff = None if current_tradeoff is None else 8.0 * (1.0 + 0.01 * 10.0)

    scenarios = []

    def add_scenario(name: str, updates: dict[str, float], note: str):
        factors = dict(current_factors)
        factors.update(updates)
        value = _recompute(factors)
        required = None
        if isinstance(value, (int, float)) and value not in (None, 0) and isinstance(ep_value, (int, float)):
            required = ep_value / value
        scenarios.append({
            'scenario': name,
            'package_value': value,
            'relative_delta_pct': None if value in (None, 0) or not isinstance(ep_value, (int, float)) else ((value - ep_value) / ep_value) * 100.0,
            'required_residual_multiplier_to_match_ep': required,
            'note': note,
        })

    add_scenario(
        'current_package_semantics',
        {},
        'Current calculator semantics: standard perk and trade-off perk improve the delta only; enhancement handled as direct multiplier row.'
    )

    if ep_standard is not None:
        add_scenario(
            'ep_standard_perk_semantics_only',
            {standard_key: ep_standard},
            'EP EPH_REGEN formula multiplies the full perk result by Standard Perks Bonus rather than scaling only the perk delta.'
        )

    if ep_tradeoff is not None:
        add_scenario(
            'ep_tradeoff_semantics_only',
            {tradeoff_key: ep_tradeoff},
            'EP EPH_REGEN formula applies Improve Trade-Off Perks to the full x8 regen multiplier rather than scaling only the +7 delta.'
        )

    if ep_standard is not None and ep_tradeoff is not None:
        add_scenario(
            'ep_perk_semantics_bundle',
            {standard_key: ep_standard, tradeoff_key: ep_tradeoff},
            'Apply both EP-style perk semantics while leaving the rest of the calculator unchanged.'
        )
        bundle_value = scenarios[-1]['package_value']
        residual_after_bundle = scenarios[-1]['required_residual_multiplier_to_match_ep']
    else:
        bundle_value = None
        residual_after_bundle = None

    inferred_wse_level_after_bundle = None
    integer_wse_candidate = None
    integer_wse_multiplier = None
    if isinstance(residual_after_bundle, (int, float)) and residual_after_bundle > 0:
        inferred_wse_level_after_bundle = (residual_after_bundle - 1.0) / 0.01
        integer_wse_candidate = round(inferred_wse_level_after_bundle)
        integer_wse_multiplier = 1.0 + 0.01 * integer_wse_candidate
        add_scenario(
            'ep_perk_semantics_plus_inferred_wse',
            {
                standard_key: ep_standard,
                tradeoff_key: ep_tradeoff,
                enhancement_key: (current_enhancement or 1.0) * integer_wse_multiplier,
            },
            'Model the remaining residual as an EP-only WSE multiplier applied on top of the existing enhancement multiplier. This is a semantic audit scenario, not a calculator truth claim.'
        )

    return {
        'destination': dest,
        'compare_state_key': row.get('compare_state_key'),
        'compare_preset': row.get('compare_preset'),
        'compare_perk_state': row.get('compare_perk_state'),
        'package_value': package_value,
        'ep_value': ep_value,
        'package_value_recomputed_from_current_factors': package_from_factors,
        'current_factors': {
            'standard_perk_factor': current_standard,
            'tradeoff_regen_factor': current_tradeoff,
            'enhancement_factor': current_enhancement,
        },
        'ep_formula_hypotheses': {
            'ep_standard_perk_factor': ep_standard,
            'ep_tradeoff_regen_factor': ep_tradeoff,
            'residual_multiplier_after_ep_perk_semantics': residual_after_bundle,
            'inferred_wse_level_after_ep_perk_semantics': inferred_wse_level_after_bundle,
            'nearest_integer_wse_level_candidate': integer_wse_candidate,
            'nearest_integer_wse_multiplier': integer_wse_multiplier,
        },
        'scenarios': scenarios,
        'assessment': {
            'best_fit_hypothesis': 'EP regen delta is largely explained by EP-specific semantics: full-result standard perk scaling, full-result trade-off scaling, and an unresolved WSE multiplier near +8%.',
            'calculator_change_recommended': False,
            'reason': 'These semantics appear to be EP workbook behavior and are not yet KB-backed as true in-game calculator rules.'
        }
    }






# --- tower damage / defense / hp reports ---
def _project_funding_cash_evidence() -> dict:
    return {
        'assumed_cash': PROJECTED_RUNTIME_COMPARE_CASH_ASSUMPTIONS[(_state('tower_damage'), 'Project Funding')]['cash'],
        'evidence_strength': 'user_provided_for_current_ep_compare_basis',
        'note': 'User clarified that EP uses 50b cash for Project Funding compare. This is treated as an explicit compare-policy input rather than a calculator truth claim.',
    }


def _build_tower_damage_runtime_gap_report(ep_compare: dict) -> dict:
    dest = _state('tower_damage')
    row = (ep_compare or {}).get(dest) or {}
    base_value = row.get('package_value_before_runtime_assumptions')
    package_value = row.get('package_value')
    ep_value = row.get('ep_value')
    assumptions = list(row.get('runtime_compare_assumptions') or [])
    applied_runtime_multiplier = None
    if isinstance(base_value, (int, float)) and base_value not in (None, 0) and isinstance(package_value, (int, float)):
        applied_runtime_multiplier = package_value / base_value
    required_total_runtime_multiplier = None
    if isinstance(base_value, (int, float)) and base_value not in (None, 0) and isinstance(ep_value, (int, float)):
        required_total_runtime_multiplier = ep_value / base_value

    pf_cash = PROJECTED_RUNTIME_COMPARE_CASH_ASSUMPTIONS[(_state('tower_damage'), 'Project Funding')]['cash']
    pf_coeff = PROJECT_FUNDING_RARITY_COEFFICIENTS['Mythic']
    pf_multiplier = 1.0 + math.log10(float(pf_cash)) * float(pf_coeff)
    required_berserker_if_pf_fixed = None
    if required_total_runtime_multiplier is not None and pf_multiplier not in (None, 0):
        required_berserker_if_pf_fixed = required_total_runtime_multiplier / pf_multiplier

    scenarios = []
    def add_scenario(name: str, runtime_multiplier: float | None, note: str):
        value = None if runtime_multiplier is None or base_value in (None, 0) else float(base_value) * float(runtime_multiplier)
        required = None
        if isinstance(value, (int, float)) and value not in (None, 0) and isinstance(ep_value, (int, float)):
            required = ep_value / value
        scenarios.append({
            'scenario': name,
            'runtime_multiplier': runtime_multiplier,
            'package_value': value,
            'relative_delta_pct': None if value in (None, 0) or not isinstance(ep_value, (int, float)) else ((value - ep_value) / ep_value) * 100.0,
            'required_residual_multiplier_to_match_ep': required,
            'note': note,
        })

    add_scenario('current_package_runtime_assumptions', applied_runtime_multiplier, 'Current compare-only runtime assumptions as emitted by the package.')
    add_scenario('ep_cash_50b_with_berserker_x8', 8.0 * pf_multiplier, 'EP compare uses Project Funding cash assumption of 50b; this scenario keeps Berserker at x8 and swaps only the PF cash assumption.')
    if required_berserker_if_pf_fixed is not None:
        add_scenario('ep_cash_50b_with_fitted_berserker', required_berserker_if_pf_fixed * pf_multiplier, 'Diagnostic only: if 50b cash is fixed, this is the Berserker multiplier that would exactly close the EP row.')

    return {
        'destination': dest,
        'compare_state_key': row.get('compare_state_key'),
        'compare_preset': row.get('compare_preset'),
        'compare_perk_state': row.get('compare_perk_state'),
        'package_value_before_runtime_assumptions': base_value,
        'package_value_after_runtime_assumptions': package_value,
        'ep_value': ep_value,
        'runtime_compare_assumptions': assumptions,
        'ep_evidence': _project_funding_cash_evidence(),
        'current_assumption_parameters': {
            'project_funding_cash_assumption': pf_cash,
            'project_funding_rarity_family': 'Mythic',
            'project_funding_multiplier_at_assumed_cash': pf_multiplier,
            'berserker_assumption_multiplier': 8.0,
        },
        'derived_fit': {
            'applied_runtime_multiplier': applied_runtime_multiplier,
            'required_total_runtime_multiplier_to_match_ep': required_total_runtime_multiplier,
            'required_berserker_multiplier_if_project_funding_cash_assumption_fixed': required_berserker_if_pf_fixed,
        },
        'assessment': {
            'calculator_change_recommended': False,
            'compare_assumption_change_recommended': True,
            'reason': 'tower_damage residue sits in the compare-only runtime normalization layer, not the base damage resolver. With EP cash assumption fixed at 50b, the current x8 Berserker assumption nearly exactly closes the EP row.',
        },
        'scenarios': scenarios,
    }


def _build_tower_defense_absolute_semantic_gap_report(ep_compare: dict) -> dict:
    dest = _state('tower_defense_absolute')
    row = (ep_compare or {}).get(dest) or {}
    contributors = row.get('package_contributors') or []

    workshop_base = None
    current_factors = {}
    for c in contributors:
        family = c.get('source_family')
        name = c.get('source_name')
        key = f"{family}::{name}"
        value = c.get('value')
        try:
            vf = float(value)
        except Exception:
            vf = None
        factor = None
        if vf is None:
            factor = None
        elif family == 'workshop':
            workshop_base = vf
        elif family == 'module_substat' and c.get('value_type') == 'percent_display':
            factor = 1.0 + (vf / 100.0)
        elif family == 'enhancement':
            factor = vf
        elif family in {'relic', 'vault'}:
            factor = 1.0 + vf
        else:
            factor = vf if vf > 1.0 else 1.0 + vf
        if factor is not None:
            current_factors[key] = factor

    def _recompute(factors: dict[str, float]) -> float | None:
        if workshop_base is None:
            return None
        out = workshop_base
        for _, factor in factors.items():
            out *= factor
        return out

    package_value = row.get('package_value')
    ep_value = row.get('ep_value')
    recomputed = _recompute(current_factors)

    standard_key = 'perk::x1.15 Defense Absolute'
    current_standard = current_factors.get(standard_key)
    ep_standard = None if current_standard is None else (1.0 + 5.0 * 0.15) * (1.0 + 0.01 * 25.0)

    scenarios = []

    def add_scenario(name: str, updates: dict[str, float], note: str):
        factors = dict(current_factors)
        factors.update(updates)
        value = _recompute(factors)
        required = None
        if isinstance(value, (int, float)) and value not in (None, 0) and isinstance(ep_value, (int, float)):
            required = ep_value / value
        scenarios.append({
            'scenario': name,
            'package_value': value,
            'relative_delta_pct': None if value in (None, 0) or not isinstance(ep_value, (int, float)) else ((value - ep_value) / ep_value) * 100.0,
            'required_residual_multiplier_to_match_ep': required,
            'note': note,
        })

    add_scenario('current_package_semantics', {}, 'Current calculator semantics and compare-row inputs as emitted.')
    if ep_standard is not None:
        add_scenario('ep_standard_perk_semantics_only', {standard_key: ep_standard}, 'EP Defense Absolute appears to scale the full standard-perk result by Standard Perk Bonus rather than scaling only the perk delta. This is treated as workbook semantics, not calculator truth.')

    best_fit = scenarios[-1] if scenarios else None

    return {
        'destination': dest,
        'compare_state_key': row.get('compare_state_key'),
        'compare_preset': row.get('compare_preset'),
        'compare_perk_state': row.get('compare_perk_state'),
        'package_value': package_value,
        'ep_value': ep_value,
        'package_value_recomputed_from_current_factors': recomputed,
        'current_factors': {
            'standard_perk_factor': current_standard,
        },
        'ep_formula_hypotheses': {
            'ep_standard_perk_factor': ep_standard,
            'residual_multiplier_after_ep_standard_perk_semantics': None if best_fit is None else best_fit.get('required_residual_multiplier_to_match_ep'),
        },
        'scenarios': scenarios,
        'assessment': {
            'best_fit_hypothesis': 'tower_defense_absolute EP delta is almost exactly explained by EP-style full-result Standard Perk Bonus scaling on the Defense Absolute standard perk.',
            'calculator_change_recommended': False,
            'reason': 'The package row is internally consistent and the EP value is matched almost exactly by swapping only the standard-perk semantic to the workbook-style full-result scaling.'
        }
    }


def _build_tower_hp_semantic_gap_report(ep_compare: dict) -> dict:
    dest = _state('tower_hp')
    row = (ep_compare or {}).get(dest) or {}
    contributors = row.get('package_contributors') or []

    workshop_base = None
    current_factors = {}
    for c in contributors:
        family = c.get('source_family')
        name = c.get('source_name')
        key = f"{family}::{name}"
        value = c.get('value')
        try:
            vf = float(value)
        except Exception:
            vf = None
        factor = None
        if vf is None:
            factor = None
        elif family == 'workshop':
            workshop_base = vf
        elif family == 'module_substat' and c.get('value_type') == 'percent_display':
            factor = 1.0 + (vf / 100.0)
        elif family == 'enhancement':
            factor = vf
        elif family in {'relic', 'vault'}:
            factor = 1.0 + vf
        elif family == 'module' and c.get('value_type') == 'multiplier_display':
            factor = vf if vf >= 1.0 else 1.0 + vf
        elif family == 'perk' and c.get('value_type') == 'multiplier':
            factor = vf
        else:
            factor = vf if vf >= 1.0 else 1.0 + vf
        if factor is not None:
            current_factors[key] = factor

    def _recompute(factors: dict[str, float]) -> float | None:
        if workshop_base is None:
            return None
        out = workshop_base
        for _, factor in factors.items():
            out *= factor
        return out

    package_value = row.get('package_value')
    ep_value = row.get('ep_value')
    recomputed = _recompute(current_factors)

    standard_key = 'perk::x1.20 Max Health'
    coin_to_key = 'perk::x1.80 coins, but Tower Max Health -70%'
    regen_to_key = 'perk::Tower Health Regen x8.00, But Tower Max Max Health -60%'

    current_standard = current_factors.get(standard_key)
    current_coin_to = current_factors.get(coin_to_key)
    current_regen_to = current_factors.get(regen_to_key)

    ep_standard = None if current_standard is None else (1.0 + 0.2 * 5.0) * (1.0 + 0.01 * 25.0)

    scenarios = []

    def add_scenario(name: str, updates: dict[str, float], note: str):
        factors = dict(current_factors)
        factors.update(updates)
        value = _recompute(factors)
        required = None
        if isinstance(value, (int, float)) and value not in (None, 0) and isinstance(ep_value, (int, float)):
            required = ep_value / value
        scenarios.append({
            'scenario': name,
            'package_value': value,
            'relative_delta_pct': None if value in (None, 0) or not isinstance(ep_value, (int, float)) else ((value - ep_value) / ep_value) * 100.0,
            'required_residual_multiplier_to_match_ep': required,
            'note': note,
        })

    add_scenario('current_package_semantics', {}, 'Current calculator semantics and compare-row inputs as emitted.')
    if ep_standard is not None:
        add_scenario('ep_standard_perk_semantics_only', {standard_key: ep_standard}, 'EP EPH_HEALTH formula multiplies the full perk result by Standard Perks Bonus. This is an EP workbook scenario, not a calculator truth claim.')

    dwhp_level = None
    ids_lines = (ROOT / 'input' / 'imports' / 'ids.csv').read_text().splitlines()
    for line in ids_lines:
        if line.startswith('Death Wave Health,'):
            try:
                dwhp_level = int(line.split(',', 1)[1].strip())
            except Exception:
                dwhp_level = None
            break
    dwhp_multiplier = None if dwhp_level is None else (5.0 + 0.25 * dwhp_level)
    dwhp_key = 'lab::Death Wave Health'
    current_dwhp = current_factors.get(dwhp_key)
    armor_primary = current_factors.get('module::Sharp Fortitude')
    armor_assist = current_factors.get('module::Orbital Augment')

    if dwhp_multiplier is not None and current_dwhp is None:
        add_scenario('current_package_plus_account_dwhp', {'runtime::Death Wave Health': dwhp_multiplier}, 'Model account Death Wave Health as an extra compare-only multiplier to test whether missing run-state bonus explains the EP delta. This is diagnostic only.')
    if ep_standard is not None and current_standard not in (None, 0):
        add_scenario('current_package_with_ep_standard_perk_semantics', {standard_key: ep_standard}, 'Model EP workbook full-result Standard Perk Bonus semantics on top of the current package contributors.')

    return {
        'destination': dest,
        'compare_state_key': row.get('compare_state_key'),
        'compare_preset': row.get('compare_preset'),
        'compare_perk_state': row.get('compare_perk_state'),
        'package_value': package_value,
        'ep_value': ep_value,
        'package_value_recomputed_from_current_factors': recomputed,
        'current_factors': {
            'standard_perk_factor': current_standard,
            'coin_health_tradeoff_factor': current_coin_to,
            'regen_health_tradeoff_factor': current_regen_to,
            'death_wave_health_factor': current_dwhp,
            'armor_primary_factor': armor_primary,
            'armor_assist_factor': armor_assist,
        },
        'ep_formula_hypotheses': {
            'ep_standard_perk_factor': ep_standard,
            'account_death_wave_health_level': dwhp_level,
            'account_death_wave_health_multiplier_if_applied': dwhp_multiplier,
        },
        'assessment': {
            'remaining_fraction_bug_present_in_live_compare_row': False if (current_coin_to is not None and current_regen_to is not None and abs(current_coin_to - 0.3) < 1e-9 and abs(current_regen_to - 0.4) < 1e-9) else None,
            'death_wave_health_wired_in_live_compare_row': current_dwhp == dwhp_multiplier if (current_dwhp is not None and dwhp_multiplier is not None) else None,
            'reason': 'Current compare row carries the two HP trade-off drawbacks correctly and now also includes the Death Wave Health multiplier plus the EP-style armor assist factor. The remaining gap is primarily the EP workbook Standard Perk Bonus semantic drift.',
            'calculator_change_recommended': False,
        },
        'scenarios': scenarios,
    }


# --- section ---
def _build_kb_only_health_family_audit(stat_inputs, statbook_rows: dict) -> dict:
    relevant_destinations = {
        'tower_hp', 'tower_regen', 'wall_hp', 'wall_regen', 'package_chance_pct'
    }
    relevant_rows = [
        row for row in stat_inputs
        if (row.destination_id in relevant_destinations)
        or ('health' in (row.stat_name or '').lower())
        or ('regen' in (row.stat_name or '').lower())
        or ('package' in (row.stat_name or '').lower())
        or ('wall' in (row.stat_name or '').lower())
    ]
    unmapped_relevant = [
        {
            'source_family': row.source_family,
            'stat_name': row.stat_name,
            'value': row.value,
            'value_type': row.value_type,
            'notes': row.notes,
        }
        for row in relevant_rows if not row.destination_id
    ]
    grouped = {}
    for destination in sorted(relevant_destinations):
        row = statbook_rows.get(_state(destination))
        if not row:
            continue
        grouped[destination] = {
            'status': row.get('status'),
            'final_value': row.get('final_value'),
            'display_value': row.get('display_value'),
            'contributor_families': sorted({c.get('source_family') for c in row.get('contributors', []) if c.get('source_family')}),
            'contributors': [
                {
                    'source_family': c.get('source_family'),
                    'source_name': c.get('source_name'),
                    'value': c.get('value'),
                    'display_value': c.get('display_value'),
                    'value_type': c.get('value_type'),
                    'notes': c.get('notes'),
                }
                for c in row.get('contributors', [])
            ],
        }
    findings = [
        {
            'severity': 'high',
            'surface': 'package_chance_pct',
            'finding': 'Workshop package-chance formula was inconsistent with KB and corrected in this iteration.',
            'kb_basis': 'KB workshop summary states 6% base and +0.40 percentage points per level, max 30% workshop-only.',
            'fix_applied': "WORKSHOP_FORMULA_VALUES['Package Chance'] changed from 10 + 0.5*level to 6 + 0.4*level.",
        },
        {
            'severity': 'high',
            'surface': 'tower_hp',
            'finding': 'tower_hp relic semantics were previously too vague in the KB. They are now repaired to explicit pct_bonus semantics, consistent with live-wiki guidance that relic bonuses are additive with similar relics and multiplicative with other bonuses.',
            'kb_basis': 'kb/global-rules/tables/relic-input-registry.csv now uses semantic_unit_hint pct_bonus for relic__tower__health__pct.',
            'fix_applied': 'Publish policy re-enabled in the destination formula ledger.',
        },
        {
            'severity': 'high',
            'surface': 'tower_regen',
            'finding': 'tower_regen relic semantics were previously too vague in the KB. They are now repaired to explicit pct_bonus semantics, consistent with live-wiki guidance that relic bonuses are additive with similar relics and multiplicative with other bonuses.',
            'kb_basis': 'kb/global-rules/tables/relic-input-registry.csv now uses semantic_unit_hint pct_bonus for relic__tower__health_regen__pct.',
            'fix_applied': 'Publish policy re-enabled in the destination formula ledger.',
        },
        {
            'severity': 'high',
            'surface': 'wall_hp',
            'finding': 'wall_hp KB semantics were repaired by aligning Wall Health lab application metadata to the wiki-verified percent ladder.',
            'kb_basis': 'kb/labs/tables/lab-application-registry.csv now classifies LAB_WALL_HEALTH as additive_percent_points / percent_points and points to the dedicated wall-health table.',
            'fix_applied': 'Publish policy re-enabled in the destination formula ledger.',
        },
        {
            'severity': 'high',
            'surface': 'wall_regen',
            'finding': 'wall_regen can publish again because upstream tower_regen contract ambiguity was repaired and the wall-regen lab was already represented as a percent ladder in the KB.',
            'kb_basis': 'Current phase-3 override derives wall_regen from tower_regen multiplied by wall-only contributors; wall regen lab table remains wiki-verified percent values.',
            'fix_applied': 'Publish policy re-enabled in the destination formula ledger.',
        },
    ]
    return {
        'scope': 'kb_only_health_family_audit',
        'display_rule': 'rendered/exported display fields use k, M, B, T, q, Q, s, S abbreviations; raw numeric values remain unchanged',
        'strict_kb_publish_recommendation': {
            'block_destinations': [],
            'allow_destinations': ['package_chance_pct', 'tower_hp', 'tower_regen', 'wall_hp', 'wall_regen'],
            'reason': 'Strict KB-only governance now allows the health family to publish because the specific KB contract ambiguities were repaired with wiki-verified semantics.',
        },
        'surfaces': grouped,
        'unmapped_relevant_rows': unmapped_relevant,
        'findings': findings,
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


# --- scope classifiers, EP oracle, kb gap analysis ---
LAB_APPLICATION_SCOPE = {
    'Attack Speed', 'Damage', 'Health', 'Critical Factor', 'Game Speed', 'Labs Speed', 'Range',
    'Defense %', 'Recovery Package Chance', 'Enemy Attack Level Skip', 'Enemy Health Level Skip',
    'Chrono Field Duration', 'Waves Required', 'Cash Bonus', 'Coins / Kill Bonus', 'Health Regen',
}
VAULT_ADMIN_EXCLUDED = {
    'Keys spent', 'Total Bonuses', 'Misc.', 'Attack', 'Defense', 'Utility',
    'Cash / Wave', 'Coins / Kill', 'Coins / Wave', 'Interest / Wave', 'Unlocks',
}
MODULE_SCOPE_EXCLUDED = set()



EP_NONCOMPARABLE_DESTINATIONS = {
        _state('free_attack_upgrade_chance_pct'),
        _state('free_defense_upgrade_chance_pct'),
        _state('free_utility_upgrade_chance_pct'),
}

EP_LABEL_TO_DESTINATION = {
        'Attack Speed': _state('tower_attack_speed'),
        'Critical Chance': _state('tower_crit_chance_pct'),
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
        'Health': _state('tower_hp'),
        'Defense Absolute': _state('tower_defense_absolute'),
        'Defense %': _state('tower_defense_pct'),
        'Wall Fortification': _state('wall_fortification_multiplier'),
        'Wall Regen': _state('wall_regen'),
        'Max Recovery': _state('max_recovery_multiplier'),
        'Coins / Kill Bonus': _state('coins_per_kill_bonus'),
        'Free Attack Upgrade': _state('free_attack_upgrade_chance_pct'),
        'Free Defense Upgrade': _state('free_defense_upgrade_chance_pct'),
        'Free Utility Upgrade': _state('free_utility_upgrade_chance_pct'),
        'Damage': _state('tower_damage'),
}

# EP export key-level overrides for known label ambiguities.
# These are compare-policy mappings only (not calculator truth).
EP_KEY_TO_DESTINATION = {
        'crit_factor': _state('tower_crit_multiplier'),
        'health_regen': _state('tower_regen'),
        'recovery_package_chance': _state('package_chance_pct'),
        'shockwave_frequency': _state('tower_shockwave_interval_seconds'),
        'wall_health': 'derived::wall.hp_pre_fort',
        'wall_fortification': _state('wall_fortification_multiplier'),
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

def _load_ep_oracle(ep_path: Path):
    if not ep_path.exists():
        return {}
    df = pd.read_csv(ep_path, header=None)
    out = {}
    for _, row in df.iterrows():
        if len(row) < 4:
            continue
        key = str(row.iloc[1]).strip() if len(row) > 1 else ''
        label = str(row.iloc[2]).strip()
        value_raw = row.iloc[3] if len(row) > 3 else None
        destination = EP_KEY_TO_DESTINATION.get(key) or EP_LABEL_TO_DESTINATION.get(label)
        if destination is None:
            continue
        parsed, kind = _parse_ep_value(value_raw)
        if parsed is not None:
            out[destination] = {
                'label': label,
                'ep_value_raw': value_raw,
                'ep_value_parsed': parsed,
                'ep_value_type': kind,
            }
    return out


def load_ep_oracle() -> dict:
    """Public evaluator-owned EP oracle loader for orchestration consumers."""
    return _load_ep_oracle(EP_ORACLE_PATH)



def _load_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))


def _build_kb_incomplete_areas(stat_inputs, statbook_publishable_dict, formula_ledger):
    active_unmapped_inputs = []
    for row in stat_inputs:
        routing_class = classify_input_routing(row)
        if routing_class != 'truly_unrouted_unknown':
            continue
        if row.source_family == 'raw':
            continue
        active_unmapped_inputs.append({
            'source_family': row.source_family,
            'stat_name': row.stat_name,
            'value_type': row.value_type,
            'contributor_id': row.contributor_id,
            'routing_class': routing_class,
        })
    active_unmapped_inputs.sort(key=lambda item: (item['source_family'], item['stat_name']))
    active_unmapped_by_family = {}
    for item in active_unmapped_inputs:
        fam = item['source_family']
        active_unmapped_by_family[fam] = active_unmapped_by_family.get(fam, 0) + 1

    resolved_unknown_schema_units = []
    for destination_id, row in (statbook_publishable_dict.get('rows') or {}).items():
        if row.get('status') != 'resolved':
            continue
        schema = row.get('schema') or {}
        if schema.get('unit') != 'unknown':
            continue
        resolved_unknown_schema_units.append({
            'destination_id': destination_id,
            'resolver': schema.get('resolver'),
            'value_type': row.get('value_type'),
            'final_value': row.get('final_value'),
        })
    resolved_unknown_schema_units.sort(key=lambda item: item['destination_id'])

    relic_registry_rows = _load_csv_rows(ROOT / 'kb' / 'global-rules' / 'tables' / 'relic-input-registry.csv')
    ambiguous_relic_semantics = []
    for rec in relic_registry_rows:
        if (rec.get('semantic_unit_hint') or '').strip() == 'percent_points_or_pct_bonus':
            ambiguous_relic_semantics.append({
                'registry_key': rec.get('registry_key'),
                'destination_id': f"{rec.get('destination_object_type','').strip()}::{rec.get('destination_id','').strip()}" if rec.get('destination_id') else None,
            })
    ambiguous_relic_semantics.sort(key=lambda item: item['registry_key'] or '')

    return {
        'summary': {
            'active_unmapped_input_count': len(active_unmapped_inputs),
            'resolved_unknown_schema_unit_count': len(resolved_unknown_schema_units),
            'ambiguous_relic_semantic_hint_count': len(ambiguous_relic_semantics),
        },
        'priority_gaps': ([
            item for item in active_unmapped_inputs
            if item['stat_name'] == 'Dimension Core::main'
        ] + active_unmapped_inputs[:12]),
        'active_unmapped_by_family': active_unmapped_by_family,
        'active_unmapped_inputs': active_unmapped_inputs,
        'resolved_unknown_schema_units': resolved_unknown_schema_units,
        'ambiguous_relic_semantic_hints': ambiguous_relic_semantics,
        'notes': [
            'Active unmapped inputs are true unknown/unrouted calculator inputs without a destination contract in the current package.',
            'Resolved rows with schema.unit=unknown are publishable bridges, but not convergence-grade clean contracts.',
            'ambiguous_relic_semantic_hints lists KB registry rows that still admit multiple semantic interpretations and may need future wiki-backed tightening.',
        ],
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


def _build_kb_gap_register(kb_incomplete_areas, audits):
    register = []

    for item in kb_incomplete_areas.get('active_unmapped_inputs', []):
        register.append({
            'gap_id': f"unmapped::{item['source_family']}::{item['stat_name']}",
            'bucket': _classify_unmapped_input_gap(item),
            'surface': item['stat_name'],
            'files': [
                'qe/stat_input_compiler.py',
                'kb/global-rules/contracts/contributor-mappings-full.yaml',
                'kb/labs/tables/lab-application-registry.csv',
                'kb/cards/tables/card-effect-registry.csv',
                'kb/global-rules/tables/relic-input-registry.csv',
            ],
            'evidence': f"Active {item['source_family']} input remains unmapped in current package.",
            'why_it_matters': 'Live calculator input is preserved but not yet closed into a governed destination contract.',
            'what_would_close_it': 'Either add the missing KB destination/contract coverage or route the input through existing KB contracts in the compiler.',
            'changed_in_this_iteration': False,
            'verification_source': 'package KB only',
        })

    for item in kb_incomplete_areas.get('ambiguous_relic_semantic_hints', []):
        register.append({
            'gap_id': f"ambiguous_relic::{item['registry_key']}",
            'bucket': 'KB contract ambiguous',
            'surface': item.get('destination_id') or item['registry_key'],
            'files': ['kb/global-rules/tables/relic-input-registry.csv'],
            'evidence': f"semantic_unit_hint remains percent_points_or_pct_bonus for {item['registry_key']}",
            'why_it_matters': 'Ambiguous relic semantics can block strict fail-closed destination formulas.',
            'what_would_close_it': 'Resolve the relic semantic hint to a single contract form using KB evidence and wiki verification where needed.',
            'changed_in_this_iteration': False,
            'verification_source': 'package KB only',
        })

    for item in kb_incomplete_areas.get('resolved_unknown_schema_units', []):
        register.append({
            'gap_id': f"unknown_unit::{item['destination_id']}",
        'bucket': 'Intentional non-goal / runtime-only surface' if str(item['destination_id']).startswith(COMPAT_LEGACY_RUNTIME_ONLY_PREFIXES) else 'KB missing executable contract',
            'surface': item['destination_id'],
            'files': ['qe/stat_resolution.py', 'app/pipeline.py'],
            'evidence': f"Resolved publishable row still has schema.unit=unknown for {item['destination_id']}",
            'why_it_matters': 'The surface publishes, but its schema is not convergence-grade clean.',
            'what_would_close_it': 'Assign a precise schema unit or explicitly classify the surface as runtime-only/administrative.',
            'changed_in_this_iteration': False,
            'verification_source': 'package KB only',
        })

    compare_issues = audits.get('compare_layer_destination_unit_inconsistencies', []) if isinstance(audits, dict) else []
    for issue in compare_issues:
        if issue.get('status') not in {'mismatch', 'formula_blocked'}:
            continue
        register.append({
            'gap_id': f"compare::{issue.get('destination')}",
            'bucket': 'Calculator wiring / implementation gap',
            'surface': issue.get('destination'),
            'files': ['app/pipeline.py', 'qe/stat_resolution.py', 'qe/stat_input_compiler.py'],
            'evidence': f"Compare layer still reports {issue.get('status')} for {issue.get('destination')}",
            'why_it_matters': 'This is a live survivor surface after current state binding and compare normalization.',
            'what_would_close_it': 'Close the remaining contributor/formula gap or explicitly reclassify the surface as blocked/non-comparable.',
            'changed_in_this_iteration': False,
            'verification_source': 'package KB only',
        })

    # Deduplicate by gap_id while preserving order
    seen = set()
    out = []
    for entry in register:
        gid = entry['gap_id']
        if gid in seen:
            continue
        seen.add(gid)
        out.append(entry)
    summary = Counter(entry['bucket'] for entry in out)
    return {
        'summary': dict(sorted(summary.items())),
        'entries': out,
    }


def _build_publish_gate_audits(stat_inputs, statbook_dict, ep_compare, formula_ledger):
    mapped_level_rows = []

# --- publish gate audits + runtime assumptions + contributor snapshot ---
def _build_publish_gate_audits(stat_inputs, statbook_dict, ep_compare, formula_ledger):
    mapped_level_rows = []
    for row in stat_inputs:
        if row.kb_mapped and row.destination_id and row.value_type == 'level':
            mapped_level_rows.append({
                'source_family': row.source_family,
                'source_name': row.source_name,
                'destination_object_type': row.destination_object_type,
                'destination_id': row.destination_id,
                'value': row.value,
                'notes': row.notes,
            })
    resolved_with_unresolved = []
    capability_non_boolean = []
    compare_inconsistencies = []
    for key, row in statbook_dict['rows'].items():
        status = row.get('status')
        contributors = row.get('contributors', [])
        unresolved = [c for c in contributors if c.get('value_type') == 'level' or c.get('value') is None or 'unresolved' in str(c.get('notes') or '').lower()]
        if status == 'resolved' and unresolved:
            resolved_with_unresolved.append({
                'destination': key,
                'unresolved_contributors': unresolved,
            })
        if key.startswith(_CAPABILITY_PREFIX) and key.endswith('.enabled') and status == 'resolved' and not isinstance(row.get('final_value'), bool):
            capability_non_boolean.append({
                'destination': key,
                'final_value': row.get('final_value'),
                'status': status,
            })
    for dest, compare in ep_compare.items():
        pkg_row = statbook_dict['rows'].get(dest)
        if pkg_row is None:
            compare_inconsistencies.append({
                'destination': dest,
                'issue': 'missing_from_package',
                'ep_label': compare.get('label'),
            })
            continue
        pkg_unit = pkg_row.get('value_type')
        ep_type = compare.get('ep_value_type')
        ep_value = compare.get('ep_value_parsed')
        status = compare.get('status')
        notes = set(compare.get('compare_notes') or [])
        expected_pct = dest.endswith('_pct')
        if expected_pct and ep_type == 'number' and ep_value is not None and ep_value <= 1.0:
            compare_inconsistencies.append({
                'destination': dest,
                'issue': 'ep_decimal_fraction_percent_surface',
                'package_unit': pkg_unit,
                'ep_type': ep_type,
                'normalized_ep_percent_points': ep_value * 100.0,
                'package_value': compare.get('package_value'),
                'status': status,
            })
        if 'ep_compare_uses_unsupported_stage_facets' in notes:
            compare_inconsistencies.append({
                'destination': dest,
                'issue': 'stage_scope_gap',
                'unsupported_facets': [note for note in compare.get('compare_notes', []) if note in {'max_progression', 'max_workshop', 'run_perks'}],
                'compare_preset': compare.get('compare_preset'),
                'status': status,
            })
        if status in {'non_comparable', 'non_numeric_compare', 'formula_blocked'}:
            compare_inconsistencies.append({
                'destination': dest,
                'issue': status,
                'compare_preset': compare.get('compare_preset'),
            })
    return {
        'mapped_rows_still_level': mapped_level_rows,
        'resolved_stats_with_unresolved_contributors': resolved_with_unresolved,
        'capability_destinations_non_boolean': capability_non_boolean,
        'blocked_boolean_type_mismatches': [r['stat_name'] for r in statbook_dict['rows'].values() if r.get('status')=='mapped_not_resolved' and 'boolean' in (r.get('notes') or '')],
        'compare_layer_destination_unit_inconsistencies': compare_inconsistencies,
    }

def _apply_projected_runtime_compare_assumptions(destination: str, package_row: dict | None, stage_context: dict) -> tuple[dict | None, list[str]]:
    if package_row is None:
        return None, []
    if stage_context.get('package_progression_state') != 'projected_max_progression':
        return package_row, []
    compare_preset = stage_context.get('compare_preset')
    active_cards = set((stage_context.get('active_cards_by_preset') or {}).get(compare_preset) or [])
    adjusted = dict(package_row)
    notes = []
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


def _normalize_module_rarity_family(rarity: str | None) -> str | None:
    if not rarity:
        return None
    rarity = str(rarity).strip()
    for base in ('Ancestral', 'Mythic', 'Legendary', 'Epic'):
        if rarity.startswith(base):
            return base
    return rarity


def _project_funding_compare_multiplier(stage_context: dict) -> tuple[float | None, str | None]:
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
    rarity_family = _normalize_module_rarity_family(module_row.get('rarity'))
    coeff = PROJECT_FUNDING_RARITY_COEFFICIENTS.get(rarity_family)
    cash = assumption.get('cash')
    if coeff is None or not cash or cash <= 0:
        return None, None
    multiplier = max(1.0, 1.0 + math.log10(float(cash)) * float(coeff))
    note = f"{assumption['note']}__rarity_family_{rarity_family.lower()}__multiplier_{multiplier:.6f}"
    return multiplier, note


def _contributor_snapshot(row: dict | None) -> list[dict]:
    if not isinstance(row, dict):
        return []
    out = []
    for c in row.get('contributors', []) or []:
        out.append({
            'source_family': c.get('source_family'),
            'source_name': c.get('source_name'),
            'preset_name': c.get('preset_name'),
            'value': c.get('value'),
            'value_type': c.get('value_type'),
            'notes': c.get('notes'),
        })
    return out



# --- section ---
def _build_run_perk_residue_analysis(ep_compare: dict) -> dict:
    out = {
        'lineage_backed_destinations': sorted(COMPARE_DESTINATION_RUN_PERK_FACETS.keys()),
        'stage_scope_rows': [],
    }
    for destination, row in sorted(ep_compare.items()):
        if row.get('status') != 'stage_scope_mismatch':
            continue
        if destination not in COMPARE_DESTINATION_RUN_PERK_FACETS:
            continue
        try:
            package_value = float(row.get('package_value'))
        except Exception:
            package_value = None
        try:
            ep_value = float(row.get('ep_value'))
        except Exception:
            ep_value = None
        required_effective_multiplier = None
        if package_value not in (None, 0.0) and ep_value is not None:
            required_effective_multiplier = ep_value / package_value
        out['stage_scope_rows'].append({
            'destination': destination,
            'package_value': package_value,
            'ep_value': ep_value,
            'required_effective_multiplier_to_match_ep': required_effective_multiplier,
            'unsupported_facets': list(row.get('unsupported_compare_facets') or []),
            'compare_notes': list(row.get('compare_notes') or []),
        })
    out['stage_scope_row_count'] = len(out['stage_scope_rows'])
    return out

def _build_tradeoff_routing_audit(
    compiled_rows,
    perk_entities: dict,
    tradeoff_benefit_effect_indexes: dict,
    banned_ids: set[str],
    *,
    preset: str,
    state_mode: str,
    perk_state: str,
) -> dict:

    by_perk = {}
    for row in compiled_rows:
        if row.source_family != 'perk' or not row.contributor_id or '::effect_' not in row.contributor_id:
            continue
        contrib = row.contributor_id
        if not contrib.startswith('perk::'):
            continue
        perk_id = contrib.split('::', 2)[1]
        meta = perk_entities.get(perk_id, {})
        if str(meta.get('category') or '').strip().lower() != 'trade_off':
            continue
        by_perk.setdefault(perk_id, []).append(row)

    perk_rows = []
    active_tradeoff_count = 0
    compile_error_count = 0
    banned_present = []
    for perk_id, meta in sorted(perk_entities.items()):
        if str(meta.get('category') or '').strip().lower() != 'trade_off':
            continue
        rows_for_perk = by_perk.get(perk_id, [])
        active = len(rows_for_perk) > 0
        if active:
            active_tradeoff_count += 1
        if perk_id in banned_ids and active:
            banned_present.append(perk_id)
        benefit_indexes = set(tradeoff_benefit_effect_indexes.get(perk_id, set()))
        compiled_indexes = set()
        destinations = []
        benefit_rows = 0
        drawback_rows = 0
        for row in rows_for_perk:
            effect_index = (row.contributor_id or '').rsplit('_', 1)[-1]
            compiled_indexes.add(effect_index)
            destinations.append({
                'effect_index': effect_index,
                'destination_object_type': row.destination_object_type,
                'destination_id': row.destination_id,
                'value': row.value,
                'value_type': row.value_type,
            })
            if effect_index in benefit_indexes:
                benefit_rows += 1
            else:
                drawback_rows += 1
        expected_two_sided = bool(benefit_indexes)
        both_sides_materialized = active and benefit_rows > 0 and drawback_rows > 0
        compile_error = active and expected_two_sided and not both_sides_materialized
        if compile_error:
            compile_error_count += 1
        perk_rows.append({
            'perk_id': perk_id,
            'perk_name': meta.get('perk_name'),
            'active': active,
            'banned': perk_id in banned_ids,
            'compiled_effect_indexes': sorted(compiled_indexes),
            'benefit_effect_indexes': sorted(benefit_indexes),
            'benefit_rows': benefit_rows,
            'drawback_rows': drawback_rows,
            'both_sides_materialized': both_sides_materialized,
            'compile_error': compile_error,
            'destinations': destinations,
        })

    return {
        'perk_state': perk_state,
        'preset': preset,
        'state_mode': state_mode,
        'active_tradeoff_count': active_tradeoff_count,
        'compile_error_count': compile_error_count,
        'banned_tradeoffs_present_count': len(banned_present),
        'banned_tradeoffs_present': banned_present,
        'rows': perk_rows,
    }

def _build_tower_damage_residue_analysis(ep_compare: dict) -> dict:
    row = ep_compare.get(_state('tower_damage')) or {}
    pre_runtime = row.get('package_value_before_runtime_assumptions')
    post_runtime = row.get('package_value')
    ep_value = row.get('ep_value')
    assumptions = list(row.get('runtime_compare_assumptions') or [])

    def _as_float(value):
        try:
            return float(value)
        except Exception:
            return None

    pre_runtime_f = _as_float(pre_runtime)
    post_runtime_f = _as_float(post_runtime)
    ep_value_f = _as_float(ep_value)

    applied_runtime_multiplier = None
    required_total_runtime_multiplier = None
    required_project_funding_multiplier_if_berserker_x8 = None
    required_project_funding_coefficient_at_cash_500b_if_berserker_x8 = None
    residue = None
    residue_relative_pct = None

    if pre_runtime_f not in (None, 0.0) and post_runtime_f is not None:
        applied_runtime_multiplier = post_runtime_f / pre_runtime_f
    if pre_runtime_f not in (None, 0.0) and ep_value_f is not None:
        required_total_runtime_multiplier = ep_value_f / pre_runtime_f
    if required_total_runtime_multiplier is not None:
        required_project_funding_multiplier_if_berserker_x8 = required_total_runtime_multiplier / 8.0
        cash = 500_000_000_000.0
        required_project_funding_coefficient_at_cash_500b_if_berserker_x8 = (required_project_funding_multiplier_if_berserker_x8 - 1.0) / math.log10(cash)
    if post_runtime_f is not None and ep_value_f is not None:
        residue = post_runtime_f - ep_value_f
        if ep_value_f != 0:
            residue_relative_pct = 100.0 * residue / ep_value_f

    return {
        'destination': _state('tower_damage'),
        'package_value_before_runtime_assumptions': pre_runtime_f,
        'package_value_after_runtime_assumptions': post_runtime_f,
        'ep_value': ep_value_f,
        'runtime_compare_assumptions': assumptions,
        'applied_runtime_multiplier': applied_runtime_multiplier,
        'required_total_runtime_multiplier_to_match_ep': required_total_runtime_multiplier,
        'required_project_funding_multiplier_at_berserker_x8_to_match_ep': required_project_funding_multiplier_if_berserker_x8,
        'required_project_funding_coefficient_at_cash_50b_if_berserker_x8_to_match_ep': required_project_funding_coefficient_at_cash_500b_if_berserker_x8,
        'residue_after_current_assumptions': residue,
        'residue_relative_pct_after_current_assumptions': residue_relative_pct,
    }



# --- perk contributor audit, compare situation fit, compare rows builder ---
def _build_perk_contributor_audit(stat_inputs_by_preset: dict[str, list]) -> dict:
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
        stat_inputs = stat_inputs_by_preset.get(preset_name, [])
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




def _build_compare_situation_fit_matrix(compare_by_state_key: dict) -> dict:
    views = {}
    best_fit_by_destination = {}
    for state_key, payload in compare_by_state_key.items():
        preset = payload.get('preset')
        perk_state = payload.get('perk_state')
        compare = payload.get('compare', {})
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

def _build_compare_rows_by_preset(prepared_bundle: PreparedCompareRowsBundle):
    return (
        prepared_bundle.account_state,
        prepared_bundle.compare_rows_by_preset,
        prepared_bundle.compare_publishable_rows_by_preset,
        prepared_bundle.package_stage_context,
    )





def _is_calculator_scope_row(row) -> bool:
    if row.source_family == 'lab':
        return row.stat_name in LAB_APPLICATION_SCOPE
    if row.source_family == 'vault':
        return row.stat_name not in VAULT_ADMIN_EXCLUDED
    if row.source_family == 'module':
        return row.stat_name not in MODULE_SCOPE_EXCLUDED
    return row.source_family in {'workshop', 'enhancement', 'relic', 'bot', 'guardian', 'uw', 'uw_plus', 'module', 'module_substat', 'card', 'vault', 'lab'}



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


def _build_perk_coverage_audit(
    perk_entities: dict,
    perk_effects: dict,
    perk_target_destination_overrides: dict,
    audit_rows: list,
    canonical_stats,
    alias_index: dict,
    perks_input_path: Path | None,
):
    _perk_entities, perk_effects, perk_target_destination_overrides, resolve_destination = _load_perk_compiler_metadata(
        perk_entities,
        perk_effects,
        perk_target_destination_overrides,
    )

    canon_stats = canonical_stats
    audit_row_index = Counter()
    sample_row_index = {}
    for row in audit_rows:
        m = re.search(r'perk::(.+?)::effect_(\d+)$', row.contributor_id or '')
        if not m:
            continue
        perk_id, effect_index = m.group(1), m.group(2)
        audit_row_index[(perk_id, effect_index)] += 1
        sample_row_index.setdefault((perk_id, effect_index), row)

    summary = Counter()
    destination_summary = Counter()
    per_perk = []
    for perk_id, meta in sorted(perk_entities.items()):
        effects = perk_effects.get(perk_id, [])
        effect_details = []
        perk_categories = set()
        for effect in effects:
            effect_index = effect.get('effect_index', '').strip()
            operation = effect.get('operation', '').strip()
            target_stat_id = effect.get('target_stat_id', '').strip()
            route_category = 'unbound'
            destination_object_type, destination_id, from_alias = resolve_destination(
                target_stat_id,
                canon_stats=canon_stats,
                alias_index=alias_index,
                perk_target_destination_overrides=perk_target_destination_overrides,
            )
            if destination_object_type is not None and destination_id is not None:
                route_category = (
                    f'routed_alias::{destination_object_type}'
                    if from_alias
                    else (
                        'routed::canonical_stat_direct'
                        if destination_object_type == 'canonical_stat' and target_stat_id in canon_stats
                        else f'routed::{destination_object_type}'
                    )
                )
            operation_supported = _perk_operation_supported(operation)
            picks = int(meta.get('max_picks') or 1)
            compiled_count = audit_row_index.get((perk_id, effect_index), 0)
            sample_row = sample_row_index.get((perk_id, effect_index))
            expected_rows = picks
            compile_status = 'compiled' if compiled_count >= 1 else 'missing_compiled_row'
            if route_category == 'unbound':
                coverage = 'unbound_target'
            elif not operation_supported:
                coverage = 'unsupported_operation'
            elif compile_status != 'compiled':
                coverage = 'compile_gap'
            elif destination_object_type == 'canonical_stat':
                coverage = 'canonical_stat_routed'
            elif destination_object_type in {'runtime_mechanic_param', 'mechanic_param', 'environment_param', 'meta_progression_param'}:
                coverage = 'runtime_param_routed'
            elif destination_object_type in {'capability', 'account_flag'}:
                coverage = 'capability_routed'
            else:
                coverage = 'other_routed'
            summary[coverage] += 1
            destination_summary[destination_object_type or 'unbound'] += 1
            perk_categories.add(coverage)
            effect_details.append({
                'effect_index': effect_index,
                'target_stat_id': target_stat_id,
                'operation': operation,
                'effect_value': effect.get('effect_value', '').strip(),
                'scope': effect.get('scope', '').strip(),
                'route_category': route_category,
                'destination_object_type': destination_object_type,
                'destination_id': destination_id,
                'operation_supported': operation_supported,
                'compile_status': compile_status,
                'coverage': coverage,
                'compiled_row_count': compiled_count,
                'expected_row_count_from_max_picks': expected_rows,
                'sample_compiled_row': None if sample_row is None else {
                    'destination_object_type': sample_row.destination_object_type,
                    'destination_id': sample_row.destination_id,
                    'value_type': sample_row.value_type,
                    'resolver_id': sample_row.resolver_id,
                    'kb_mapped': sample_row.kb_mapped,
                },
            })
        per_perk.append({
            'perk_id': perk_id,
            'perk_name': meta.get('perk_name'),
            'category': meta.get('category'),
            'max_picks': meta.get('max_picks'),
            'stacking_type': meta.get('stacking_type'),
            'effect_count': len(effect_details),
            'coverage_categories': sorted(perk_categories),
            'effects': effect_details,
        })

    return {
        'entity_count': len(perk_entities),
        'effect_count': sum(len(v) for v in perk_effects.values()),
        'input_file': _relpath_str(perks_input_path),
        'active_perk_state_source': 'input_owned_perk_surface',
        'summary_by_coverage': dict(sorted(summary.items())),
        'summary_by_destination_object_type': dict(sorted(destination_summary.items())),
        'all_perks_compile_audit_row_count': len(audit_rows),
        'perks': per_perk,
    }
