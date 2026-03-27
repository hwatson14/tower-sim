"""
app/pipeline.py -- Layer wiring.

Owns: wiring input -> qe -> simulators -> evaluators -> advisors,
output assembly, pipeline configuration.
Must not own: domain logic.

T12: bridge removed; all _h.* calls resolved to real owners.
Domain helpers live in their real owners (evaluators.compare, input.loader).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Active layer imports
from qe.stat_input_compiler import (
    compile_stat_inputs,
    normalize_state_mode,
    SUPPORTED_STATE_MODES,
    state_mode_support,
)
from app.display import (
    annotate_compare_display_fields as _annotate_compare_display_fields,
    annotate_display_fields as _annotate_display_fields,
)
from evaluators.compare import (
    build_compare_status_summary as _build_compare_status_summary,
    build_ep_compare as _build_ep_compare,
    build_line_by_line_verification as _build_line_by_line_verification,
    build_survivability_residue_analysis as _build_survivability_residue_analysis,
    build_survivor_closure_report as _build_survivor_closure_report,
    ensure_compare_authoritative_verdict_fields as _ensure_compare_authoritative_verdict_fields,
    ensure_line_verification_authoritative_verdict_fields as _ensure_line_verification_authoritative_verdict_fields,
    _normalize_perk_state,
    _perks_enabled_for_state,
    _load_formula_ledger,
    _load_ep_oracle,
    _build_compare_rows_by_preset,
    _formula_contract,
    _build_publishable_statbook,
    _ep_stage_context_for_destination,
    _compare_state_key_for_destination,
    _contributor_snapshot,
    _apply_projected_runtime_compare_assumptions,
    _normalize_compare_values,
    _is_calculator_scope_row,
    _build_publish_gate_audits,
    _build_kb_incomplete_areas,
    _build_kb_gap_register,
    COMPARE_PRESET_OVERRIDES,
    COMPARE_DESTINATION_RUN_PERK_FACETS,
    _sanitized_active_perk_preset,
    _sanitized_configured_perk_presets,
    _sanitized_account_state_for_output,
    _build_audit_surface_manifest,
    _build_artifact_contract_manifest,
    _build_family_completeness_matrix,
    _build_kb_only_health_family_audit,
    _build_damage_defabs_scope_audit,
    _build_perk_coverage_audit,
    _build_tower_damage_residue_analysis,
    _build_run_perk_residue_analysis,
    _build_tradeoff_routing_audit,
    _build_perk_contributor_audit,
    _build_compare_situation_fit_matrix,
    _build_tower_regen_closure_report,
    _build_tower_hp_semantic_gap_report,
    _build_tower_regen_ep_semantic_gap_report,
    _build_tower_defense_absolute_semantic_gap_report,
    _build_tower_damage_runtime_gap_report,
)
from input.loader import _resolve_perk_config
from evaluators.scorer import compute_optimizer_scores
from input.loader import load_inputs
from input.parsers import parse_ids
from qe.publication import publish_phase3_query_surfaces
from qe.routing import resolve_stats


# ---------------------------------------------------------------------------
# T9 bounding: pipeline-local utilities inlined from run_stats.
# These are orchestration-adjacent helpers; remaining * calls are domain
# builders legitimately in run_stats pending T-post-9 extraction.
# ---------------------------------------------------------------------------
FORMULA_LEDGER_PATH = ROOT / 'kb' / 'ledgers' / 'formula_surface_policy.yaml'


def _load_json_config(path: Path) -> dict:
    import json
    return json.loads(path.read_text(encoding='utf-8'))


def _safe_pct(n: int, d: int) -> float:
    return round((100.0 * n / d), 2) if d else 0.0


def _relpath_str(path_like) -> str:
    p = Path(path_like)
    try:
        return str(p.resolve().relative_to(ROOT))
    except Exception:
        try:
            return str(p.relative_to(ROOT))
        except Exception:
            return str(p)


def _json_sanitize(obj):
    if isinstance(obj, Path):
        return _relpath_str(obj)
    if isinstance(obj, dict):
        return {k: _json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_sanitize(v) for v in obj]
    if isinstance(obj, tuple):
        return [_json_sanitize(v) for v in obj]
    if isinstance(obj, str) and obj.startswith('/'):
        try:
            return _relpath_str(obj)
        except Exception:
            return obj
    return obj



def run_pipeline(args) -> int:
    """
    Execute the full stat pipeline.

    Wires: input -> qe -> evaluators -> out.
    Transitional domain helpers sourced from run_stats module until T7.
    """
    args.state_mode = normalize_state_mode(args.state_mode)
    args.perk_state = _normalize_perk_state(args.perk_state)
    args.out.mkdir(parents=True, exist_ok=True)

    ids_raw = parse_ids(args.ids)
    _manual_inputs_path = getattr(args, 'manual_inputs', None)
    _input_bundle = load_inputs(ids_path=args.ids, manual_inputs_path=_manual_inputs_path)
    loadout_config = _input_bundle.loadout_config
    perk_config, perk_config_resolution = _resolve_perk_config(
        _input_bundle.perk_config, args.state_mode, ids_raw=ids_raw,
        diag_output_dir=args.out / 'diagnostics' / 'perks',
    )
    formula_ledger = _load_formula_ledger(FORMULA_LEDGER_PATH)
    ep_oracle = _load_ep_oracle(ROOT / 'input' / 'imports' / 'ep_export.csv')

    (
        account_state,
        compare_rows_by_preset,
        compare_publishable_rows_by_preset,
        package_stage_context,
    ) = _build_compare_rows_by_preset(
        ids_raw=ids_raw,
        loadout_config=loadout_config,
        perk_config=perk_config,
        formula_ledger=formula_ledger,
        state_mode=args.state_mode,
        default_preset=args.preset,
        ep_oracle=ep_oracle,
        perk_state=args.perk_state,
    )

    perks_enabled = _perks_enabled_for_state(account_state.active_perk_preset, args.perk_state)
    stat_inputs = compile_stat_inputs(
        account_state,
        preset_name=args.preset,
        state_mode=args.state_mode,
        perks_enabled=perks_enabled,
    )
    statbook = resolve_stats(stat_inputs)
    publish_phase3_query_surfaces(statbook.rows, account_state_labs=account_state.labs)
    statbook_dict = statbook.to_dict()
    for destination, row in statbook_dict.get('rows', {}).items():
        row['formula_contract'] = _formula_contract(formula_ledger, destination)
    _annotate_display_fields(statbook_dict)
    statbook_publishable_dict = _build_publishable_statbook(statbook_dict, formula_ledger)
    _annotate_display_fields(statbook_publishable_dict)

    state_matrix = {}
    for state_mode in SUPPORTED_STATE_MODES:
        matrix_inputs = compile_stat_inputs(
            account_state,
            preset_name=args.preset,
            state_mode=state_mode,
            perks_enabled=perks_enabled,
        )
        matrix_statbook_obj = resolve_stats(matrix_inputs)
        publish_phase3_query_surfaces(matrix_statbook_obj.rows, account_state_labs=account_state.labs)
        matrix_statbook = matrix_statbook_obj.to_dict()
        state_matrix[state_mode] = {
            'support': state_mode_support(state_mode),
            'input_count': len(matrix_inputs),
            'mapped_input_count': sum(1 for r in matrix_inputs if r.kb_mapped),
            'resolved_stat_count': matrix_statbook.get('diagnostics', {}).get('resolved_stat_count', 0),
            'partially_resolved_stat_count': matrix_statbook.get('diagnostics', {}).get('partially_resolved_stat_count', 0),
        }

    _ep_kwargs = dict(
        ep_stage_context_for_destination=_ep_stage_context_for_destination,
        compare_state_key_for_destination=_compare_state_key_for_destination,
        contributor_snapshot=_contributor_snapshot,
        apply_projected_runtime_compare_assumptions=_apply_projected_runtime_compare_assumptions,
        formula_contract=_formula_contract,
        normalize_compare_values=_normalize_compare_values,
    )
    ep_compare = _build_ep_compare(
        ep_oracle, compare_rows_by_preset, formula_ledger, package_stage_context, **_ep_kwargs
    )
    ep_compare_publishable = _build_ep_compare(
        ep_oracle, compare_publishable_rows_by_preset, formula_ledger, package_stage_context, **_ep_kwargs
    )
    _annotate_compare_display_fields(ep_compare)
    _annotate_compare_display_fields(ep_compare_publishable)
    current_compare_summary = _build_compare_status_summary(ep_compare_publishable)

    (
        projected_account_state,
        projected_compare_rows_by_preset,
        projected_compare_publishable_rows_by_preset,
        projected_stage_context,
    ) = _build_compare_rows_by_preset(
        ids_raw=ids_raw,
        loadout_config=loadout_config,
        perk_config=perk_config,
        formula_ledger=formula_ledger,
        state_mode='max_progression',
        default_preset=args.preset,
        ep_oracle=ep_oracle,
        perk_state=args.perk_state,
    )
    projected_ep_compare_publishable = _build_ep_compare(
        ep_oracle, projected_compare_publishable_rows_by_preset, formula_ledger,
        projected_stage_context, **_ep_kwargs
    )
    _annotate_compare_display_fields(projected_ep_compare_publishable)
    projected_compare_summary = _build_compare_status_summary(projected_ep_compare_publishable)

    unmapped_examples = {}
    for row in stat_inputs:
        if not row.kb_mapped and row.source_family not in unmapped_examples:
            unmapped_examples[row.source_family] = row.stat_name

    mapped_counter = Counter(row.source_family for row in stat_inputs if row.kb_mapped)
    total_counter = Counter(row.source_family for row in stat_inputs)

    card_preset_sizes = {name: len(cards) for name, cards in account_state.card_presets.items()}
    card_slot_limit_exceeded = {
        name: size
        for name, size in card_preset_sizes.items()
        if account_state.card_slots_unlocked is not None and size > account_state.card_slots_unlocked
    }

    resolved_surface_count = statbook.diagnostics.get('resolved_stat_count', 0)
    partial_surface_count = statbook.diagnostics.get('partially_resolved_stat_count', 0)
    mapped_input_count = sum(1 for row in stat_inputs if row.kb_mapped)
    total_input_count = len(stat_inputs)
    family_burn_down = {
        family: {
            'mapped': mapped_counter.get(family, 0),
            'total': total_counter.get(family, 0),
            'pct': _safe_pct(mapped_counter.get(family, 0), total_counter.get(family, 0)),
        }
        for family in sorted(total_counter)
    }
    scoped_rows = [row for row in stat_inputs if _is_calculator_scope_row(row)]
    scoped_total = len(scoped_rows)
    scoped_mapped = sum(1 for row in scoped_rows if row.kb_mapped)
    scope_excluded_rows = [row for row in stat_inputs if not _is_calculator_scope_row(row)]
    scoped_family_totals = Counter(row.source_family for row in scoped_rows)

    audits = _build_publish_gate_audits(
        stat_inputs, statbook_publishable_dict, ep_compare_publishable, formula_ledger
    )
    kb_incomplete_areas = _build_kb_incomplete_areas(
        stat_inputs, statbook_publishable_dict, formula_ledger
    )
    kb_gap_register = _build_kb_gap_register(kb_incomplete_areas, audits)
    ep_compare_publishable = _ensure_compare_authoritative_verdict_fields(ep_compare_publishable)
    line_verification = _build_line_by_line_verification(
        statbook_publishable_dict, ep_compare_publishable, formula_ledger, _formula_contract
    )
    line_verification = _ensure_line_verification_authoritative_verdict_fields(line_verification)
    survivor_closure_report = _build_survivor_closure_report(ep_compare_publishable, line_verification)
    verification_counter = Counter(v['verification_status'] for v in line_verification.values())

    diagnostics = {
        'section_names': list(ids_raw.raw_sections.keys()),
        'section_row_counts': {k: len(v) for k, v in ids_raw.raw_sections.items()},
        'default_preset': args.preset,
        'state_mode': args.state_mode,
        'perk_config_resolution': perk_config_resolution,
        'state_mode_support': state_mode_support(args.state_mode),
        'supported_state_modes': list(SUPPORTED_STATE_MODES),
        'state_matrix': state_matrix,
        'stat_input_count': len(stat_inputs),
        'statbook_row_count': len(statbook.rows),
        'engine_status': statbook.diagnostics.get('resolver_status'),
        'publish_status': statbook_publishable_dict.get('diagnostics', {}).get('oracle_policy'),
        'formula_ledger_version': formula_ledger.get('version'),
        'ep_compare_stage_rules': {
            'default_compare_preset': 'Farming',
            'preset_overrides': COMPARE_PRESET_OVERRIDES,
            'ep_progression_state': 'max_progression',
            'ep_workshop_state': 'derived_from_max_progression',
            'ep_run_state_default': 'farming',
            'ep_run_state_tourney_offense': 'tourney_present',
            'package_compare_capability': {
                'progression_state': 'dynamic_current_or_projected_max_by_state_mode',
                'workshop_state': 'dynamic_current_or_projected_max_by_state_mode',
                'perk_state': args.perk_state,
                'perk_materialization': perks_enabled,
                'perk_ids_parser_support': False,
                'perk_external_config_support': True,
                'perk_account_state_support': True,
                'perk_stat_input_support': True,
                'perk_resolver_support': True,
                'perk_account_state_support': True,
                'active_perk_preset': _sanitized_active_perk_preset(account_state, args.preset),
                'state_mode': args.state_mode,
            },
            'notes': [
                'EP export compare uses run-situation policy: offense surfaces use Tourney loadout with perks off; non-offense surfaces use Farming by default and follow the selected engine perk state.',
                'EP export max progression implies max workshop and farming-side perk application beyond the current IDS/loadout-present package state.',
                f"The current package can store externally selected perk presets from manual_inputs.yaml, compile perk stat inputs, and resolve supported perk contributors into final stats.",
                'Perk selections are not parsed from IDS itself; they must be supplied explicitly when a run state needs them.',
                'Perk application is controlled at engine scope via --perk-state auto|on|off; perks are either materialized for the run or fully disabled.',
                'When values do not match and EP uses unsupported stage facets, compare status is stage_scope_mismatch rather than a hard formula mismatch.',
                'Max Recovery EP export is treated as a non-comparable health-at-cap surface, not a multiplier.',
            ],
        },
        'destination_type_schema': statbook.diagnostics.get('destination_type_schema', {}),
        'mapped_stat_input_count': mapped_input_count,
        'unmapped_stat_input_count': sum(1 for row in stat_inputs if not row.kb_mapped),
        'resolved_stat_count': resolved_surface_count,
        'partially_resolved_stat_count': partial_surface_count,
        'burn_down': {
            'input_mapping_pct': _safe_pct(mapped_input_count, total_input_count),
            'fully_resolved_surface_pct_of_inputs': _safe_pct(resolved_surface_count, total_input_count),
            'resolved_or_partial_surface_pct_of_inputs': _safe_pct(
                resolved_surface_count + partial_surface_count, total_input_count
            ),
            'family_mapping_pct': family_burn_down,
            'calculator_scope_total_inputs': scoped_total,
            'calculator_scope_mapped_inputs': scoped_mapped,
            'calculator_scope_mapping_pct': _safe_pct(scoped_mapped, scoped_total),
            'calculator_scope_excluded_inputs': len(scope_excluded_rows),
            'calculator_scope_excluded_examples': sorted({row.stat_name for row in scope_excluded_rows})[:20],
            'calculator_scope_family_totals': dict(sorted(scoped_family_totals.items())),
            'calculator_scope_unmapped_examples': sorted({row.stat_name for row in scoped_rows if not row.kb_mapped})[:20],
            'note': 'calculator_scope excludes preserved-only lab/admin/runtime rows and grouping/admin surfaces that are intentionally outside the current calculator publish surface.',
        },
        'tests_passed': 'not_run_by_run_stats',
        'calculator_scope_mapping_pct': _safe_pct(scoped_mapped, scoped_total),
        'calculator_scope_excluded_inputs': len(scope_excluded_rows),
        'calculator_scope_unmapped_examples': sorted({row.stat_name for row in scoped_rows if not row.kb_mapped})[:20],
        'card_slots_unlocked': account_state.card_slots_unlocked,
        'active_perk_preset': _sanitized_active_perk_preset(account_state, args.preset),
        'configured_perk_presets': _sanitized_configured_perk_presets(account_state, args.preset),
        'active_card_preset': account_state.active_card_preset,
        'active_module_preset': account_state.active_module_preset,
        'perk_input_file': 'manual_inputs.yaml',
        'compare_package_value_provenance': {
            'statbook_default_output_preset': args.preset,
            'ep_compare_uses_rows_by_preset': True,
            'preset_overrides': COMPARE_PRESET_OVERRIDES,
            'note': 'ep_oracle_compare package_value may differ from statbook.json when compare_preset differs from the default output preset.',
        },
        'kb_incomplete_areas': kb_incomplete_areas,
        'kb_gap_register': kb_gap_register,
        'blocked_formula_contract_count': kb_incomplete_areas['summary']['blocked_formula_contract_count'],
        'active_unmapped_input_count': kb_incomplete_areas['summary']['active_unmapped_input_count'],
        'resolved_unknown_schema_unit_count': kb_incomplete_areas['summary']['resolved_unknown_schema_unit_count'],
        'ambiguous_relic_semantic_hint_count': kb_incomplete_areas['summary']['ambiguous_relic_semantic_hint_count'],
        'perk_support': {
            'perk_ids_parser_support': False,
            'perk_ids_parser_note': 'Perk selections are not parsed from IDS; they are supplied through external perk config.',
            'perk_external_config_support': True,
            'perk_account_state_support': True,
            'perk_stat_input_support': True,
            'perk_resolver_support': True,
            'perk_state': args.perk_state,
            'perk_materialization': perks_enabled,
        },
        'card_preset_sizes': card_preset_sizes,
        'card_slot_limit_exceeded': card_slot_limit_exceeded,
        'mapped_count_by_family': dict(sorted(mapped_counter.items())),
        'total_count_by_family': dict(sorted(total_counter.items())),
        'unmapped_example_by_family': unmapped_examples,
        'ep_compare_summary': current_compare_summary,
        **current_compare_summary,
        'ep_compare_projection_views': {
            'current_state_mode': {
                'state_mode': args.state_mode,
                'perk_state': args.perk_state,
                'active_perk_preset': _sanitized_active_perk_preset(account_state, args.preset),
                **current_compare_summary,
            },
            'projected_max_progression': {
                'state_mode': 'max_progression',
                'perk_state': args.perk_state,
                'active_perk_preset': _sanitized_active_perk_preset(projected_account_state, args.preset),
                **projected_compare_summary,
            },
        },
        'lineage_backed_run_perk_destinations': sorted(COMPARE_DESTINATION_RUN_PERK_FACETS.keys()),
        'compare_layer_destination_unit_inconsistencies': audits.get('compare_layer_destination_unit_inconsistencies', []),
        'audits': audits,
        'line_verification_summary': dict(sorted(verification_counter.items())),
        'presentation': {
            'scope': 'display_fields_only',
            'raw_value_policy': 'preserve_full_precision_raw_numeric_values',
            'abbreviations': ['k', 'M', 'B', 'T', 'q', 'Q', 's', 'S'],
            'percent_policy': 'pct_and_percent_display_render_with_percent_sign',
            'multiplier_policy': 'multiplier_and_multiplier_display_render_with_leading_x',
        },
        'kb_only_health_family_audit': _build_kb_only_health_family_audit(
            stat_inputs, statbook_publishable_dict['rows']
        ),
        'kb_only_damage_defense_absolute_scope_audit': _build_damage_defabs_scope_audit(
            account_state, stat_inputs, statbook_publishable_dict['rows']
        ),
        'perk_coverage_audit': _build_perk_coverage_audit(
            ids_raw, account_state, statbook.diagnostics.get('destination_type_schema', {}), None,
        ),
        'tower_damage_residue_analysis': _build_tower_damage_residue_analysis(
            projected_ep_compare_publishable if args.state_mode != 'max_progression' else ep_compare_publishable
        ),
        'run_perk_residue_analysis': _build_run_perk_residue_analysis(
            projected_ep_compare_publishable if args.state_mode != 'max_progression' else ep_compare_publishable
        ),
        'tradeoff_routing_audit': _build_tradeoff_routing_audit(
            ids_raw, loadout_config, perk_config,
            preset=args.preset, state_mode=args.state_mode, perk_state=args.perk_state,
        ),
        'perk_contributor_audit': _build_perk_contributor_audit(
            ids_raw, loadout_config, perk_config, args.state_mode, args.preset
        ),
        'compare_situation_fit_matrix': _build_compare_situation_fit_matrix(
            ids_raw, loadout_config, perk_config, formula_ledger, ep_oracle
        ),
    }
    diagnostics['survivability_residue_analysis'] = _build_survivability_residue_analysis(
        ep_compare_publishable, diagnostics['compare_situation_fit_matrix'], statbook_dict
    )
    diagnostics['tower_regen_closure_report'] = _build_tower_regen_closure_report(ep_compare_publishable)
    diagnostics['tower_hp_semantic_gap_report'] = _build_tower_hp_semantic_gap_report(ep_compare_publishable)
    diagnostics['tower_regen_ep_semantic_gap_report'] = _build_tower_regen_ep_semantic_gap_report(ep_compare_publishable)
    diagnostics['tower_defense_absolute_semantic_gap_report'] = _build_tower_defense_absolute_semantic_gap_report(ep_compare_publishable)
    diagnostics['tower_damage_runtime_gap_report'] = _build_tower_damage_runtime_gap_report(ep_compare_publishable)
    diagnostics['compare_situation_policy'] = {
        'tournament': {
            'preset': 'Tourney',
            'perk_state': package_stage_context.get('perk_state_by_preset', {}).get('Tourney', 'off'),
        },
        'farming': {
            'preset': 'Farming',
            'perk_state': package_stage_context.get('perk_state_by_preset', {}).get('Farming', args.perk_state),
        },
        'milestone_engine': {
            'preset': args.preset,
            'perk_state': package_stage_context.get('perk_state_by_preset', {}).get(args.preset, args.perk_state),
        },
        'milestone_compare_policy': {
            'preset': 'Milestone',
            'perk_state': 'on',
            'note': 'Milestone is a real engine preset with perks on, but EP compare excludes milestone loadout.',
        },
        'policy_note': 'Perks are controlled by run situation. Tournament compare uses Tourney loadout with perks off; farming follows the selected engine perk state; milestone is a real engine preset with perks on, but EP compare excludes milestone loadout.',
    }
    diagnostics['perk_support'] = diagnostics['ep_compare_stage_rules']['package_compare_capability']

    # Remove stale output files
    stale_outputs = [
        'ep_oracle_compare_backfilled.json',
        'statbook_oracle_backfilled.json',
        'destination_formula_ledger.json',
        'forensic_debug_focus.json',
    ]
    for stale_name in stale_outputs:
        stale_path = args.out / stale_name
        if stale_path.exists():
            stale_path.unlink()

    # Write outputs
    _js = _json_sanitize
    (args.out / 'diagnostics.json').write_text(json.dumps(_js(diagnostics), indent=2, default=str))
    (args.out / 'account_state.json').write_text(
        json.dumps(_js(_sanitized_account_state_for_output(account_state, args.preset)), indent=2, default=str)
    )
    (args.out / 'stat_inputs.json').write_text(
        json.dumps(_js([row.to_dict() for row in stat_inputs]), indent=2, default=str)
    )
    (args.out / 'statbook.json').write_text(json.dumps(_js(statbook_dict), indent=2, default=str))
    (args.out / 'statbook_publishable.json').write_text(
        json.dumps(_js(statbook_publishable_dict), indent=2, default=str)
    )
    (args.out / 'ep_oracle_compare.json').write_text(
        json.dumps(_js(ep_compare_publishable), indent=2, default=str)
    )
    (args.out / 'line_by_line_verification.json').write_text(
        json.dumps(_js(line_verification), indent=2, default=str)
    )
    (args.out / 'survivor_closure_report.json').write_text(
        json.dumps(_js(survivor_closure_report), indent=2, default=str)
    )
    (args.out / 'tower_regen_closure_report.json').write_text(
        json.dumps(_js(diagnostics['tower_regen_closure_report']), indent=2, default=str)
    )
    (args.out / 'tower_hp_semantic_gap_report.json').write_text(
        json.dumps(_js(diagnostics['tower_hp_semantic_gap_report']), indent=2, default=str)
    )
    (args.out / 'tower_regen_ep_semantic_gap_report.json').write_text(
        json.dumps(_js(diagnostics['tower_regen_ep_semantic_gap_report']), indent=2, default=str)
    )
    (args.out / 'tower_defense_absolute_semantic_gap_report.json').write_text(
        json.dumps(_js(diagnostics['tower_defense_absolute_semantic_gap_report']), indent=2, default=str)
    )
    (args.out / 'tower_damage_runtime_gap_report.json').write_text(
        json.dumps(_js(diagnostics['tower_damage_runtime_gap_report']), indent=2, default=str)
    )
    (args.out / 'state_matrix.json').write_text(json.dumps(_js(state_matrix), indent=2, default=str))
    (args.out / 'audit_surface_manifest.json').write_text(
        json.dumps(_js(_build_audit_surface_manifest(account_state, args.preset)), indent=2, default=str)
    )
    (args.out / 'artifact_contract_manifest.json').write_text(
        json.dumps(
            _js(_build_artifact_contract_manifest(account_state, args.preset, stat_inputs, statbook_dict)),
            indent=2,
            default=str,
        )
    )
    (args.out / 'family_completeness_matrix.json').write_text(
        json.dumps(_js(_build_family_completeness_matrix(account_state, stat_inputs)), indent=2, default=str)
    )
    optimizer_scores = compute_optimizer_scores(statbook_dict)
    (args.out / 'optimizer_scores.json').write_text(json.dumps(_js(optimizer_scores), indent=2, default=str))
    verification_rows = [{'destination': k, **v} for k, v in line_verification.items()]
    verification_df = pd.DataFrame(verification_rows)
    verification_df.to_csv(args.out / 'line_by_line_verification.csv', index=False)

    return 0
