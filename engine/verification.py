from __future__ import annotations

import re
from collections import Counter
from typing import Callable



def kb_alignment_status_from_compare_status(compare_status: str | None) -> str:
    if compare_status in {None, 'not_in_ep'}:
        return 'not_ep_compared'
    if compare_status in {'match', 'close'}:
        return 'aligned'
    if compare_status in {'stage_scope_mismatch', 'formula_blocked', 'not_comparable'}:
        return 'not_comparable'
    return 'misaligned'


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


def annotate_compare_display_fields(ep_compare: dict, format_display_value: Callable[[object, object], str | None], format_display_number: Callable[[object], str | None]) -> None:
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
        'canonical_stat::tower_regen',
        'canonical_stat::tower_hp',
        'canonical_stat::tower_defense_absolute',
        'canonical_stat::tower_damage',
        'canonical_stat::wall_hp',
        'canonical_stat::wall_regen',
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
                if destination in {'canonical_stat::wall_hp', 'canonical_stat::wall_regen'}
                else 'primary_upstream_survivor'
            ),
        })
    return {
        'survivor_order': tracked,
        'rows': rows,
    }


def build_survivability_residue_analysis(ep_compare: dict, compare_situation_fit_matrix: dict, statbook_dict: dict) -> dict:
    destinations = [
        'canonical_stat::tower_hp',
        'canonical_stat::tower_regen',
        'canonical_stat::tower_defense_absolute',
        'canonical_stat::wall_hp',
        'canonical_stat::wall_regen',
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
    tower_hp_ratio = analysis.get('canonical_stat::tower_hp', {}).get('package_to_ep_ratio')
    wall_hp_ratio = analysis.get('canonical_stat::wall_hp', {}).get('package_to_ep_ratio')
    tower_regen_ratio = analysis.get('canonical_stat::tower_regen', {}).get('package_to_ep_ratio')
    wall_regen_ratio = analysis.get('canonical_stat::wall_regen', {}).get('package_to_ep_ratio')
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
            if vt == 'level':
                level_rows.append(c.get('source_name') or c.get('stat_name'))
            if c.get('value') is None or 'unresolved' in notes or vt in {'missing_inventory', 'raw_text', 'display_token'}:
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
        if compare_status == 'formula_blocked':
            issues.append('formula_blocked_pending_exact_destination_logic')
        verification_status = 'publishable'
        if key.startswith('raw::'):
            verification_status = 'trace_only'
        elif row.get('status') != 'resolved':
            verification_status = 'not_resolved'
        if contract.get('publish_policy') == 'block' and not key.startswith('raw::'):
            verification_status = 'blocked_formula_pending'
        elif issues:
            if key.startswith('raw::'):
                verification_status = 'trace_only'
            else:
                verification_status = 'blocked' if row.get('status') == 'resolved' else 'needs_work'
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
