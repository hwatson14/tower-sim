"""
app/pipeline.py -- Layer wiring.

Owns: wiring input -> qe -> simulators -> evaluators -> advisors,
output assembly, pipeline configuration.
Must not own: domain logic.

T12: bridge removed; all _h.* calls resolved to real owners.
Domain helpers live in their real owners (evaluators.compare, input.loader).
"""
from __future__ import annotations

import csv
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
from evaluators.scorer import compute_optimizer_scores
from input.loader import load_inputs
from input.ids_parser import parse_ids
from qe.publication import publish_phase3_query_surfaces
from qe.routing import resolve_stats
from simulators.perk_timeline_generator import (
    PerkTimelinePolicy,
    generate_timeline_from_policy,
    perk_state_at_wave,
)


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


def _write_core_outputs(
    *,
    out_dir: Path,
    diagnostics: dict,
    account_state,
    canonical_output_preset: str,
    stat_inputs,
    statbook_dict: dict,
    statbook_publishable_dict: dict,
    ep_compare_publishable: dict,
    line_verification: dict,
    survivor_closure_report: dict,
    state_matrix: dict,
    optimizer_scores: dict,
    audit_surface_manifest: dict,
    artifact_contract_manifest: dict,
    family_completeness_matrix: dict,
) -> None:
    js = _json_sanitize
    (out_dir / 'diagnostics.json').write_text(json.dumps(js(diagnostics), indent=2, default=str))
    (out_dir / 'account_state.json').write_text(
        json.dumps(js(_sanitized_account_state_for_output(account_state, canonical_output_preset)), indent=2, default=str)
    )
    (out_dir / 'stat_inputs.json').write_text(
        json.dumps(js([row.to_dict() for row in stat_inputs]), indent=2, default=str)
    )
    (out_dir / 'statbook.json').write_text(json.dumps(js(statbook_dict), indent=2, default=str))
    (out_dir / 'statbook_publishable.json').write_text(
        json.dumps(js(statbook_publishable_dict), indent=2, default=str)
    )
    (out_dir / 'ep_oracle_compare.json').write_text(
        json.dumps(js(ep_compare_publishable), indent=2, default=str)
    )
    (out_dir / 'line_by_line_verification.json').write_text(
        json.dumps(js(line_verification), indent=2, default=str)
    )
    (out_dir / 'survivor_closure_report.json').write_text(
        json.dumps(js(survivor_closure_report), indent=2, default=str)
    )
    (out_dir / 'state_matrix.json').write_text(json.dumps(js(state_matrix), indent=2, default=str))
    (out_dir / 'audit_surface_manifest.json').write_text(
        json.dumps(js(audit_surface_manifest), indent=2, default=str)
    )
    (out_dir / 'artifact_contract_manifest.json').write_text(
        json.dumps(js(artifact_contract_manifest), indent=2, default=str)
    )
    (out_dir / 'family_completeness_matrix.json').write_text(
        json.dumps(js(family_completeness_matrix), indent=2, default=str)
    )
    (out_dir / 'optimizer_scores.json').write_text(json.dumps(js(optimizer_scores), indent=2, default=str))
    verification_rows = [{'destination': k, **v} for k, v in line_verification.items()]
    pd.DataFrame(verification_rows).to_csv(out_dir / 'line_by_line_verification.csv', index=False)


def _perk_config_has_active_preset(config: dict) -> bool:
    if not isinstance(config, dict):
        return False
    active = config.get('active_perk_preset')
    presets = config.get('perk_presets') or {}
    return bool(active) and active in presets and bool(presets.get(active))


def _normalize_perk_mode(perk_mode: str | None) -> str:
    value = str(perk_mode or 'max_progression_policy').strip().lower()
    if value not in {'none', 'max_progression_policy', 'runtime_timeline'}:
        raise ValueError(f'Unsupported perk mode: {perk_mode}')
    return value


def _load_perk_entity_registry() -> list[dict]:
    path = ROOT / 'kb' / 'perks' / 'tables' / 'perk-entity-registry.csv'
    rows = []
    with path.open('r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append({k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()})
    return rows


def _default_tradeoff_alias_map() -> dict[str, str]:
    return {
        "TO1": "x1.50 Tower Damage, but Bosses Have 8x Health",
        "TO2": "x1.80 coins, but Tower Max Health -70%",
        "TO3": "Enemies Have -50% Health, but Tower Health Regen and Lifesteal -90%",
        "TO4": "Enemies Damage -50%, but Tower Damage -50%",
        "TO5": "Ranged Enemies Attack Distance Reduced, But Tower Ranged Enemies Damage x3",
        "TO6": "Enemies Speed -40%, But Enemies Damage x2.5",
        "TO7": "x12.00 Cash Per Wave, But Enemy Kill Don't Give Cash",
        "TO8": "Tower Health Regen x8.00, But Tower Max Max Health -60%",
        "TO9": "Boss Health -70%, But Boss Speed +50%",
        "TO10": "Lifesteal x2.50, But Knockback force -70%",
    }


def _resolve_policy_banned_perk_names(raw_policy: dict) -> list[str]:
    alias_map = _default_tradeoff_alias_map()
    ordered: list[str] = []
    seen: set[str] = set()
    for alias in list(raw_policy.get("banned_perk_aliases", []) or []):
        key = str(alias).strip().upper()
        name = alias_map.get(key)
        if name and name not in seen:
            ordered.append(name)
            seen.add(name)
    for name in list(raw_policy.get("banned_perks", []) or []):
        perk_name = str(name).strip()
        if perk_name and perk_name not in seen:
            ordered.append(perk_name)
            seen.add(perk_name)
    return ordered


def _ids_player_value(ids_raw, name: str, default: int = 0) -> int:
    rows = ids_raw.raw_sections.get('Player & Stuff', []) if ids_raw else []
    for row in rows:
        if row and str(row[0]).strip() == name:
            token = str(row[1]).strip() if len(row) > 1 else ''
            try:
                return int(float(token.replace(',', '')))
            except Exception:
                return default
    return default


def _resolve_manual_banned_perks(perk_policy: dict) -> list[str]:
    return _resolve_policy_banned_perk_names(perk_policy or {})


def _perk_policy_context(ids_raw, perk_policy: dict) -> tuple[dict, dict]:
    policy = perk_policy or {}
    lab_rows = ids_raw.raw_sections.get('Labs', []) if ids_raw else []
    labs = {}
    for row in lab_rows:
        if row and str(row[0]).strip():
            try:
                labs[str(row[0]).strip()] = int(float(str(row[1]).strip().replace(',', '')))
            except Exception:
                pass

    banned_names = _resolve_manual_banned_perks(policy)
    standard_perk_bonus_level = labs.get('Standard Perks Bonus', 0)
    target_wave = int(policy.get('target_wave', 50000) or 50000)
    payload = {
        'seed': int(policy.get('seed', 42) or 42),
        'target_wave': target_wave,
        'waves_required_lab': int(labs.get('Waves Required', 0) or 0),
        'standard_perk_bonus': float(standard_perk_bonus_level) / 100.0,
        'perk_option_quantity': _ids_player_value(ids_raw, 'Perk Option Quantity', 0),
        'ban_perks_capacity': max(_ids_player_value(ids_raw, 'Ban Perks', 0), len(banned_names)),
        'banned_perks': banned_names,
        'priority_order': list(policy.get('priority_order', []) or []),
        'first_perk_choice': policy.get('first_perk_choice'),
    }
    context = {
        'banned_names': banned_names,
        'standard_perk_bonus_level': standard_perk_bonus_level,
        'ban_perks_capacity_ids': _ids_player_value(ids_raw, 'Ban Perks', 0),
        'banned_perk_aliases': list(policy.get('banned_perk_aliases', []) or []),
    }
    return payload, context


def _build_max_progression_policy_perk_config(ids_raw, perk_policy: dict) -> tuple[dict, dict]:
    metadata = {
        'requested_perks_path': 'manual_inputs.yaml:perk_policy',
        'resolved_perks_path': 'manual_inputs.yaml:perk_policy',
        'fallback_applied': False,
        'fallback_reason': None,
    }
    policy_payload, context = _perk_policy_context(ids_raw, perk_policy)
    entities = _load_perk_entity_registry()
    banned_names = set(context['banned_names'])
    selections = []
    for row in entities:
        perk_id = row.get('perk_id')
        perk_name = row.get('perk_name')
        if not perk_id or not perk_name or perk_name in banned_names:
            continue
        try:
            picks = int(row.get('max_picks') or 1)
        except Exception:
            picks = 1
        selections.append({'perk_id': perk_id, 'picks': max(1, picks)})

    generated = {
        'preset_namespace_class': 'transient',
        'perk_presets': {'ProjectedMaxPolicy_AllExceptManualBans': selections},
        'active_perk_preset': 'ProjectedMaxPolicy_AllExceptManualBans',
        'notes': 'Deterministic max-progression forecasting assumption: all perks except manual bans from the input-owned perk policy.',
        'generator': {
            'perk_mode': 'max_progression_policy',
            'manual_banned_perks': sorted(banned_names),
            'manual_banned_perk_aliases': context['banned_perk_aliases'],
            'selection_rule': 'all_perks_except_manual_bans_using_registry_max_picks',
            'target_wave': policy_payload['target_wave'],
        },
    }
    metadata.update(
        {
            'resolved_perks_path': 'manual_inputs.yaml:perk_policy',
            'perk_mode': 'max_progression_policy',
            'manual_banned_perk_count': len(banned_names),
        }
    )
    return generated, metadata


def _build_runtime_timeline_perk_config(ids_raw, perk_policy: dict, *, diag_output_dir: Path | None = None) -> tuple[dict, dict]:
    policy_payload, context = _perk_policy_context(ids_raw, perk_policy)
    policy = PerkTimelinePolicy(**policy_payload)
    timeline, diag = generate_timeline_from_policy(policy)
    taken_counts = perk_state_at_wave(timeline, policy.target_wave)
    entities = _load_perk_entity_registry()
    by_name = {row.get('perk_name'): row for row in entities if row.get('perk_name')}
    selections = []
    unknown_names = []
    for perk_name, picks in sorted(taken_counts.items()):
        meta = by_name.get(perk_name)
        if not meta or not meta.get('perk_id'):
            unknown_names.append(perk_name)
            continue
        selections.append({'perk_id': meta['perk_id'], 'picks': int(picks)})

    generated = {
        'preset_namespace_class': 'transient',
        'perk_presets': {'ProjectedRuntimeTimeline': selections},
        'active_perk_preset': 'ProjectedRuntimeTimeline',
        'notes': 'Simulator-owned runtime perk timeline projected to target_wave from the input-owned perk policy.',
        'generator': {
            'perk_mode': 'runtime_timeline',
            'target_wave': policy.target_wave,
            'manual_banned_perks': context['banned_names'],
            'manual_banned_perk_aliases': context['banned_perk_aliases'],
            'unknown_generated_perk_names': unknown_names,
            'priority_order': policy.priority_order or [],
            'first_perk_choice': policy.first_perk_choice,
            'waves_required_lab': policy.waves_required_lab,
            'standard_perk_bonus_level': context['standard_perk_bonus_level'],
            'perk_option_quantity': policy.perk_option_quantity,
            'ban_perks_capacity_ids': context['ban_perks_capacity_ids'],
            'ban_perks_capacity_effective': policy.ban_perks_capacity,
        },
    }
    if diag_output_dir is not None:
        diag_output_dir.mkdir(parents=True, exist_ok=True)
        (diag_output_dir / 'perk_generation_diagnostics.json').write_text(json.dumps(diag, indent=2), encoding='utf-8')

    metadata = {
        'requested_perks_path': 'manual_inputs.yaml:perk_policy',
        'resolved_perks_path': 'simulator::runtime_timeline',
        'fallback_applied': False,
        'fallback_reason': None,
        'perk_mode': 'runtime_timeline',
        'target_wave': policy.target_wave,
    }
    if diag_output_dir is not None:
        metadata['generated_diagnostics_path'] = str(diag_output_dir / 'perk_generation_diagnostics.json')
    return generated, metadata


def _resolve_perk_config(
    *,
    perk_mode: str,
    primary_config: dict,
    perk_policy: dict,
    ids_raw,
    diag_output_dir: Path | None = None,
) -> tuple[dict, dict]:
    mode = _normalize_perk_mode(perk_mode)
    primary = primary_config if isinstance(primary_config, dict) else {}
    if mode == 'none':
        return {
            'perk_presets': {},
            'active_perk_preset': None,
        }, {
            'requested_perks_path': 'manual_inputs.yaml:perk_config',
            'resolved_perks_path': 'none',
            'fallback_applied': False,
            'fallback_reason': None,
            'perk_mode': 'none',
        }
    if mode == 'max_progression_policy':
        return _build_max_progression_policy_perk_config(ids_raw, perk_policy)
    if _perk_config_has_active_preset(primary):
        return primary, {
            'requested_perks_path': 'manual_inputs.yaml:perk_config',
            'resolved_perks_path': 'manual_inputs.yaml:perk_config',
            'fallback_applied': False,
            'fallback_reason': None,
            'perk_mode': 'runtime_timeline',
            'runtime_policy_source': 'existing_active_perk_config',
        }
    return _build_runtime_timeline_perk_config(ids_raw, perk_policy, diag_output_dir=diag_output_dir)



def run_pipeline(args) -> int:
    """
    Execute the full stat pipeline.

    Wires: input -> qe -> evaluators -> out.
    Transitional domain helpers sourced from run_stats module until T7.
    """
    args.state_mode = normalize_state_mode(args.state_mode)
    args.perk_state = _normalize_perk_state(args.perk_state)
    args.perk_mode = _normalize_perk_mode(getattr(args, 'perk_mode', None))
    args.out.mkdir(parents=True, exist_ok=True)

    ids_raw = parse_ids(args.ids)
    _manual_inputs_path = getattr(args, 'manual_inputs', None)
    _input_bundle = load_inputs(ids_path=args.ids, manual_inputs_path=_manual_inputs_path)
    loadout_config = _input_bundle.loadout_config
    perk_config, perk_config_resolution = _resolve_perk_config(
        perk_mode=args.perk_mode,
        primary_config=_input_bundle.perk_config,
        perk_policy=_input_bundle.perk_policy,
        ids_raw=ids_raw,
        diag_output_dir=args.out / 'diagnostics' / 'perks',
    )
    formula_ledger = _load_formula_ledger(FORMULA_LEDGER_PATH)
    ep_oracle = _load_ep_oracle(ROOT / 'input' / 'imports' / 'ep_export.csv')

    (
        account_state,
        compare_rows_by_preset,
        compare_publishable_rows_by_preset,
        package_stage_context,
        default_materialization,
    ) = _build_compare_rows_by_preset(
        ids_raw=ids_raw,
        loadout_config=loadout_config,
        perk_config=perk_config,
        formula_ledger=formula_ledger,
        state_mode=args.state_mode,
        default_preset=args.preset,
        ep_oracle=ep_oracle,
        perk_state=args.perk_state,
        return_default_materialization=True,
    )

    perks_enabled = _perks_enabled_for_state(account_state.active_perk_preset, args.perk_state)
    if default_materialization is None:
        stat_inputs = compile_stat_inputs(
            account_state,
            preset_name=args.preset,
            state_mode=args.state_mode,
            perks_enabled=perks_enabled,
        )
        statbook = resolve_stats(stat_inputs)
    else:
        stat_inputs = default_materialization['stat_inputs']
        statbook = default_materialization['statbook']
    publish_phase3_query_surfaces(
        statbook.rows,
        manual_advisory_inputs=_input_bundle.manual_advisory_inputs,
        account_state_labs=account_state.labs,
    )
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
        publish_phase3_query_surfaces(
            matrix_statbook_obj.rows,
            manual_advisory_inputs=_input_bundle.manual_advisory_inputs,
            account_state_labs=account_state.labs,
        )
        matrix_statbook = matrix_statbook_obj.to_dict()
        state_matrix[state_mode] = {
            'support': state_mode_support(state_mode),
            'input_count': len(matrix_inputs),
            'mapped_input_count': sum(1 for r in matrix_inputs if r.destination_id),
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

    routing_class_counts = statbook.diagnostics.get('input_routing_class_counts', {})
    routed_input_count = statbook.diagnostics.get('mapped_input_count', sum(1 for row in stat_inputs if row.destination_id))
    truly_unrouted_input_count = statbook.diagnostics.get('unmapped_input_count', sum(1 for row in stat_inputs if not row.destination_id))
    unmapped_examples = {}
    for row in stat_inputs:
        if not row.destination_id and row.source_family not in unmapped_examples:
            unmapped_examples[row.source_family] = row.stat_name

    mapped_counter = Counter(row.source_family for row in stat_inputs if row.destination_id)
    total_counter = Counter(row.source_family for row in stat_inputs)

    card_preset_sizes = {name: len(cards) for name, cards in account_state.card_presets.items()}
    card_slot_limit_exceeded = {
        name: size
        for name, size in card_preset_sizes.items()
        if account_state.card_slots_unlocked is not None and size > account_state.card_slots_unlocked
    }

    resolved_surface_count = statbook.diagnostics.get('resolved_stat_count', 0)
    partial_surface_count = statbook.diagnostics.get('partially_resolved_stat_count', 0)
    total_input_count = len(stat_inputs)
    family_burn_down = {
        family: {
            'routed': mapped_counter.get(family, 0),
            'total': total_counter.get(family, 0),
            'pct': _safe_pct(mapped_counter.get(family, 0), total_counter.get(family, 0)),
        }
        for family in sorted(total_counter)
    }
    scoped_rows = [row for row in stat_inputs if _is_calculator_scope_row(row)]
    scoped_total = len(scoped_rows)
    scoped_mapped = sum(1 for row in scoped_rows if row.destination_id)
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
        'perk_mode': args.perk_mode,
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
                'perk_mode': args.perk_mode,
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
                'EP export compare uses run-situation policy: offense surfaces use Tourney loadout with perks off; non-offense surfaces use Farming by default and follow the selected perk state/mode.',
                'EP export max progression implies max workshop and farming-side perk application beyond the current IDS/loadout-present package state.',
                'Perk policy is input-owned; pipeline selects explicit perk mode none|max_progression_policy|runtime_timeline.',
                'Perk selections are not parsed from IDS itself; they must be supplied explicitly when a run state needs them.',
                'Perk application is controlled at pipeline scope via --perk-mode plus --perk-state auto|on|off.',
                'When values do not match and EP uses unsupported stage facets, compare status is stage_scope_mismatch rather than a hard formula mismatch.',
                'Max Recovery EP export is treated as a non-comparable health-at-cap surface, not a multiplier.',
            ],
        },
        'destination_type_schema': statbook.diagnostics.get('destination_type_schema', {}),
        'mapped_stat_input_count': routed_input_count,
        'unmapped_stat_input_count': truly_unrouted_input_count,
        'input_routing_class_counts': routing_class_counts,
        'resolved_stat_count': resolved_surface_count,
        'partially_resolved_stat_count': partial_surface_count,
        'burn_down': {
            'input_mapping_pct': _safe_pct(routed_input_count, total_input_count),
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
            'calculator_scope_unmapped_examples': sorted({row.stat_name for row in scoped_rows if not row.destination_id})[:20],
            'note': 'calculator_scope tracks true unrouted inputs only; routed metadata/capability/runtime-only classes no longer inflate unmapped counts.',
        },
        'tests_passed': 'not_run_by_run_stats',
        'calculator_scope_mapping_pct': _safe_pct(scoped_mapped, scoped_total),
        'calculator_scope_excluded_inputs': len(scope_excluded_rows),
        'calculator_scope_unmapped_examples': sorted({row.stat_name for row in scoped_rows if not row.destination_id})[:20],
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
            'perk_mode': args.perk_mode,
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
        'slow_audits': {
            'include_slow_audits': bool(getattr(args, 'include_slow_audits', False)),
            'compare_situation_fit_matrix': 'enabled' if bool(getattr(args, 'include_slow_audits', False)) else 'skipped_by_default',
        },
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
        'compare_situation_fit_matrix': {
            'status': 'skipped',
            'reason': 'disabled_by_default_use_include_slow_audits',
            'destination_count': 0,
            'best_fit_by_destination': {},
            'best_fit_state_counts': {},
            'best_fit_status_counts': {},
            'states': {},
        },
    }
    if bool(getattr(args, 'include_slow_audits', False)):
        diagnostics['compare_situation_fit_matrix'] = _build_compare_situation_fit_matrix(
            ids_raw, loadout_config, perk_config, formula_ledger, ep_oracle
        )
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
            'note': 'Milestone is a real preset with perks on, but EP compare excludes milestone loadout.',
        },
        'policy_note': 'Perks are controlled by run situation. Tournament compare uses Tourney loadout with perks off; farming follows the selected perk state/mode; milestone is a real preset with perks on, but EP compare excludes milestone loadout.',
    }
    diagnostics['perk_support'] = diagnostics['ep_compare_stage_rules']['package_compare_capability']

    audit_surface_manifest = _build_audit_surface_manifest(account_state, args.preset)
    artifact_contract_manifest = _build_artifact_contract_manifest(account_state, args.preset, stat_inputs, statbook_dict)
    family_completeness_matrix = _build_family_completeness_matrix(account_state, stat_inputs)
    optimizer_scores = compute_optimizer_scores(statbook_dict)

    _write_core_outputs(
        out_dir=args.out,
        diagnostics=diagnostics,
        account_state=account_state,
        canonical_output_preset=args.preset,
        stat_inputs=stat_inputs,
        statbook_dict=statbook_dict,
        statbook_publishable_dict=statbook_publishable_dict,
        ep_compare_publishable=ep_compare_publishable,
        line_verification=line_verification,
        survivor_closure_report=survivor_closure_report,
        state_matrix=state_matrix,
        optimizer_scores=optimizer_scores,
        audit_surface_manifest=audit_surface_manifest,
        artifact_contract_manifest=artifact_contract_manifest,
        family_completeness_matrix=family_completeness_matrix,
    )

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

    (args.out / 'tower_regen_closure_report.json').write_text(
        json.dumps(_json_sanitize(diagnostics['tower_regen_closure_report']), indent=2, default=str)
    )
    (args.out / 'tower_hp_semantic_gap_report.json').write_text(
        json.dumps(_json_sanitize(diagnostics['tower_hp_semantic_gap_report']), indent=2, default=str)
    )
    (args.out / 'tower_regen_ep_semantic_gap_report.json').write_text(
        json.dumps(_json_sanitize(diagnostics['tower_regen_ep_semantic_gap_report']), indent=2, default=str)
    )
    (args.out / 'tower_defense_absolute_semantic_gap_report.json').write_text(
        json.dumps(_json_sanitize(diagnostics['tower_defense_absolute_semantic_gap_report']), indent=2, default=str)
    )
    (args.out / 'tower_damage_runtime_gap_report.json').write_text(
        json.dumps(_json_sanitize(diagnostics['tower_damage_runtime_gap_report']), indent=2, default=str)
    )
    (args.out / 'diagnostics.json').write_text(
        json.dumps(_json_sanitize(diagnostics), indent=2, default=str)
    )

    return 0
