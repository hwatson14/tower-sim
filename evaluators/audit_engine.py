"""
evaluators/audit_engine.py -- Audit and manifest generation logic.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from qe.contracts import (
    CANONICAL_PRESET_NAMES,
    sanitize_perk_presets_for_canonical_output,
    sanitize_preset_name_for_canonical_output,
)
from qe.routing import classify_input_routing


def _CAPABILITY_PREFIX():
    return 'state::capability.'


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
        if key.startswith('state::capability.') and key.endswith('.enabled') and status == 'resolved' and not isinstance(row.get('final_value'), bool):
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


def _build_kb_incomplete_areas(stat_inputs, statbook_publishable_dict, formula_ledger):
    from evaluators.compare import _formula_contract, _load_csv_rows, ROOT
    blocked_formula_contracts = []
    for destination_id, contract in (formula_ledger.get('surfaces') or {}).items():
        if contract.get('publish_policy') == 'block':
            blocked_formula_contracts.append({
                'destination_id': destination_id,
                'formula_class': contract.get('formula_class'),
                'rationale': contract.get('rationale'),
            })

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
            'blocked_formula_contract_count': len(blocked_formula_contracts),
            'active_unmapped_input_count': len(active_unmapped_inputs),
            'resolved_unknown_schema_unit_count': len(resolved_unknown_schema_units),
            'ambiguous_relic_semantic_hint_count': len(ambiguous_relic_semantics),
        },
        'priority_gaps': ([
            item for item in active_unmapped_inputs
            if item['stat_name'] == 'Dimension Core::main'
        ] + blocked_formula_contracts + active_unmapped_inputs[:12]),
        'blocked_formula_contracts': blocked_formula_contracts,
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


def _build_kb_gap_register(kb_incomplete_areas, audits):
    from evaluators.compare import COMPAT_LEGACY_RUNTIME_ONLY_PREFIXES, _classify_unmapped_input_gap
    register = []

    for item in kb_incomplete_areas.get('blocked_formula_contracts', []):
        register.append({
            'gap_id': f"formula_contract::{item['destination_id']}",
            'bucket': 'KB missing executable contract',
            'surface': item['destination_id'],
            'files': ['kb/ledgers/formula_surface_policy.yaml', 'qe/stat_resolution.py'],
            'evidence': f"publish_policy=block for {item['destination_id']}",
            'why_it_matters': 'Surface remains intentionally fail-closed until formula contract is fully closed.',
            'what_would_close_it': 'Tighten the KB/contract rationale and verify the implemented destination-specific formula is correct enough to publish.',
            'changed_in_this_iteration': False,
            'verification_source': 'package KB only',
        })

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


def _build_perk_coverage_audit(ids_raw, account_state, canonical_stats, perks_input_path: Path):
    from qe.stat_input_compiler import _load_perk_entities, _load_perk_effects, compile_stat_inputs, PERK_TARGET_DESTINATION_OVERRIDES
    from qe.query_routing import compiler_routing_indexes
    from input.state_types import PerkSelection
    from dataclasses import replace
    from evaluators.compare import _perk_operation_supported, _relpath_str

    def _slug(text: str) -> str:
        return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')

    perk_entities = _load_perk_entities()
    perk_effects = _load_perk_effects()
    _, canon_stats, alias_index, _, _ = compiler_routing_indexes()

    audit_perk_presets = {
        '__audit_all_perks__': [PerkSelection(perk_id=perk_id, picks=int(meta.get('max_picks') or 1)) for perk_id, meta in sorted(perk_entities.items())]
    }
    audit_state = replace(
        account_state,
        perk_presets=audit_perk_presets,
        perk_preset_namespace_class='transient',
        active_perk_preset='__audit_all_perks__',
    )
    audit_rows = [row for row in compile_stat_inputs(audit_state, preset_name=account_state.default_preset, state_mode='start_of_run') if row.source_family == 'perk']
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
            destination_object_type = None
            destination_id = None
            if target_stat_id in PERK_TARGET_DESTINATION_OVERRIDES:
                destination_object_type, destination_id = PERK_TARGET_DESTINATION_OVERRIDES[target_stat_id]
                route_category = f'routed::{destination_object_type}'
            elif target_stat_id in canon_stats:
                destination_object_type, destination_id = 'canonical_stat', target_stat_id
                route_category = 'routed::canonical_stat_direct'
            else:
                alias_slug = _slug(target_stat_id.replace('_', ' '))
                alias_match = alias_index.get(alias_slug)
                if alias_match is not None:
                    destination_object_type, destination_id = alias_match
                    route_category = f'routed_alias::{destination_object_type}'
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


def _build_artifact_contract_manifest(account_state, canonical_output_preset: str, stat_inputs, statbook_dict: dict) -> dict:
    from evaluators.compare import _synthetic_preset_names_present
    return {
        'version': 1,
        'canonical_output_preset': canonical_output_preset,
        'canonical_presets': list(CANONICAL_PRESET_NAMES),
        'canonical_preset_count': len(CANONICAL_PRESET_NAMES),
        'synthetic_preset_names_present': _synthetic_preset_names_present(account_state),
        'artifacts': [
            {'surface': 'account_state.json', 'artifact_class': 'canonical_snapshot', 'contract': 'full', 'provenance': 'current_run_generated', 'producer': 'run_stats.py', 'canonical': True},
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
