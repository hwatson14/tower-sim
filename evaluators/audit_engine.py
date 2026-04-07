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
    from evaluators.compare_core import _formula_contract
    from evaluators.verification_engine import _load_csv_rows
    from evaluators.compare import ROOT
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


def _build_kb_gap_register(kb_incomplete_areas, audits):
    from qe.contracts import COMPAT_LEGACY_RUNTIME_ONLY_PREFIXES
    from evaluators.audit_engine import _classify_unmapped_input_gap
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


def _build_perk_coverage_audit(
    perk_entities: dict,
    perk_effects: dict,
    perk_target_destination_overrides: dict,
    audit_rows: list,
    canonical_stats,
    alias_index: dict,
    perks_input_path: Path | None,
):
    from evaluators.audit_engine import _perk_operation_supported, _relpath_str

    def _slug(text: str) -> str:
        return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')

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
            destination_object_type = None
            destination_id = None
            if target_stat_id in perk_target_destination_overrides:
                destination_object_type, destination_id = perk_target_destination_overrides[target_stat_id]
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
    from evaluators.audit_engine import _synthetic_preset_names_present
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


# ---------------------------------------------------------------------------
# Functions migrated from compare.py (T12 shard)
# ---------------------------------------------------------------------------

def _synthetic_preset_names_present(account_state) -> list[str]:
    from qe.contracts import CANONICAL_PRESET_NAMES
    raw_names = set()
    for lane_map_name in ('card_presets', 'module_presets', 'perk_presets'):
        lane_map = getattr(account_state, lane_map_name, {}) or {}
        raw_names.update(lane_map.keys())
    return sorted(name for name in raw_names if name not in CANONICAL_PRESET_NAMES)


def _relpath_str(path_like) -> str | None:
    if path_like is None:
        return None
    from qe.contracts import relpath_str
    return relpath_str(path_like)


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
    from qe.contracts import compat_surface_from_legacy_canonical as _state_fn
    def _state(s):
        return _state_fn(s)

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


def _build_perk_contributor_audit(stat_inputs_by_preset: dict[str, list]) -> dict:
    from qe.contracts import compat_surface_from_legacy_canonical as _state_fn

    def _state(s):
        return _state_fn(s)

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
