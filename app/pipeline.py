"""
app/pipeline.py -- Layer wiring.

Owns: wiring input -> qe -> simulators -> evaluators -> advisors,
output assembly, pipeline configuration.
Must not own: domain logic.

T12: bridge removed; all _h.* calls resolved to real owners.
Orchestration utilities sharded to app/models.py and app/publication.py.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Models and Publication
from app.models import (
    PipelineRunRequest,
    PipelineRunResult,
    PipelineStageRecord,
    PipelineTrace,
    VerificationSnapshotSpec,
    FastCheckpointRequest,
    FastCheckpointResult,
    _normalize_perk_state,
    _run_stats_args_from_payload,
)
from app.publication import (
    write_core_outputs,
    write_pipeline_trace,
    _json_sanitize,
)
# Active layer imports
from qe.stat_input_compiler import (
    normalize_state_mode,
    SUPPORTED_STATE_MODES,
    state_mode_support,
)
from app.display import (
    annotate_compare_display_fields as _annotate_compare_display_fields,
    annotate_display_fields as _annotate_display_fields,
)
from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from qe.contracts import (
    sanitize_perk_presets_for_canonical_output,
    sanitize_preset_name_for_canonical_output,
    normalize_contract_payload as _contract_json_payload,
)
from qe.publication import publish_query_surfaces
from qe.routing import QEResolutionPlanner, query_response_to_statbook, resolve_checkpoint_surfaces
from qe.shared_runtime_context import get_default_qe_shared_runtime_context
from simulators.progression import resolve_run_stats_progression_bundle, run_stats_progression_family_id
from simulators.contracts import SimulatorCheckpointState
from simulators.perk_timeline_generator import (
    PerkTimelinePolicy,
    generate_timeline_from_policy,
    perk_state_at_wave,
)
from simulators.snapshot_resolver import SimulatorSnapshotResolver
from simulators.timing import compile_timing_family_rows, resolve_timing_consumer_bundle
from simulators.scenario import publish_farming_throughput_support_surfaces

# Evaluators sharded
from evaluators.compare_core import (
    build_ep_compare,
    _build_compare_rows_by_preset,
    build_compare_status_summary,
)
from evaluators.audit_engine import (
    _build_publish_gate_audits,
    _build_kb_incomplete_areas,
    _build_kb_gap_register,
    _build_perk_coverage_audit,
    _build_artifact_contract_manifest,
)
from evaluators.residue_analysis import (
    build_survivor_closure_report,
    _build_tower_regen_closure_report,
    _build_tower_hp_semantic_gap_report,
    _build_tower_damage_residue_analysis,
)
from evaluators.verification_engine import (
    build_line_by_line_verification,
    _load_ep_oracle,
)
from evaluators.compare import (
    COMPARE_DESTINATION_RUN_PERK_FACETS,
    COMPARE_PRESET_OVERRIDES,
    _apply_projected_runtime_compare_assumptions,
    _build_audit_surface_manifest,
    _build_compare_situation_fit_matrix,
    _build_damage_defabs_scope_audit,
    _build_family_completeness_matrix,
    _build_publishable_statbook,
    _compare_state_key_for_destination,
    _contributor_snapshot,
    _ep_stage_context_for_destination,
    _formula_contract,
    _load_formula_ledger,
    _normalize_compare_values,
    ensure_compare_authoritative_verdict_fields as _ensure_compare_authoritative_verdict_fields,
    ensure_line_verification_authoritative_verdict_fields as _ensure_line_verification_authoritative_verdict_fields,
)
from evaluators.scorer import compute_optimizer_scores

FORMULA_LEDGER_PATH = ROOT / 'kb' / 'ledgers' / 'formula_surface_policy.yaml'

def _relpath_str(path: Path | str | None) -> str | None:
    if path is None:
        return None
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except (ValueError, RuntimeError):
        return str(p)

def request_from_args(args) -> PipelineRunRequest:
    return PipelineRunRequest(
        ids=Path(args.ids),
        out=Path(args.out),
        preset=str(getattr(args, 'preset', 'Farming')),
        state_mode=str(getattr(args, 'state_mode', 'max_progression')),
        manual_inputs=None if getattr(args, 'manual_inputs', None) is None else Path(args.manual_inputs),
        perk_mode=str(getattr(args, 'perk_mode', 'max_progression_policy')),
        include_slow_audits=bool(getattr(args, 'include_slow_audits', False)),
        perk_state=str(getattr(args, 'perk_state', 'auto')),
    )

def _safe_pct(n: int, d: int) -> float:
    return round((100.0 * n / d), 2) if d else 0.0

def _manual_input_numeric_value(
    manual_advisory_inputs: dict,
    input_id: str,
    *,
    default: float | None = None,
) -> float | None:
    entry = (manual_advisory_inputs or {}).get(input_id)
    if not isinstance(entry, dict):
        return default
    if not entry.get('is_set', False) and entry.get('value') in (None, ''):
        return default
    try:
        return float(entry.get('value'))
    except (TypeError, ValueError):
        return default

def _merge_scenario_publication_rows(
    statbook,
    *,
    account_state,
    stat_inputs,
    preset_name: str,
    state_mode: str,
    perks_enabled: bool,
    manual_advisory_inputs: dict,
) -> None:
    scenario_config = _run_stats_scenario_config(account_state, preset_name=preset_name)
    timing_family_id = _run_stats_timing_family_id(preset_name=preset_name, perks_enabled=perks_enabled)
    farming_hours_per_day = _manual_input_numeric_value(
        manual_advisory_inputs,
        'module.farming.hours_per_day',
        default=23.5,
    )
    bound, rows = compile_timing_family_rows(
        account_state=account_state,
        family_id=timing_family_id,
        preset_name=preset_name,
        scenario_config=scenario_config,
        state_mode=state_mode,
        perks_enabled=perks_enabled,
    )
    timing_statbook = QEResolutionPlanner().resolve_rows_declared_family_statbook(
        identity=bound.binding.identity,
        stat_inputs=rows,
        family_id=timing_family_id,
        requested_surface_ids=(
            'support_surface::timing.wave_duration_seconds_effective',
        ),
        notes='run_stats scenario publication timing prerequisite merge',
        diagnostics={'source': 'app.pipeline.publish_query_surfaces'},
    )
    for surface_id, row in timing_statbook.rows.items():
        statbook.rows[surface_id] = row
    publish_farming_throughput_support_surfaces(
        statbook.rows,
        account_state=account_state,
        config=scenario_config,
        stat_inputs=stat_inputs,
        farming_hours_per_day=farming_hours_per_day,
    )

def _elapsed_ms(start: float) -> float:
    return round((perf_counter() - start) * 1000.0, 3)


def _perks_enabled_for_state(active_perk_preset: str | None, perk_state: str) -> bool:
    normalized = _normalize_perk_state(perk_state)
    if normalized == 'on':
        return True
    if normalized == 'off':
        return False
    return bool(active_perk_preset)

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

def _perk_selection_payload(account_state, perk_preset_name: str | None) -> dict:
    selections = account_state.perk_presets.get(perk_preset_name or '', []) if perk_preset_name else []
    return {
        'perk_preset_name': perk_preset_name,
        'selections': [
            {'perk_id': selection.perk_id, 'picks': selection.picks}
            for selection in selections
        ],
    }

def _preset_loadout_summary(account_state, *, preset_name: str, perk_preset_name: str | None) -> dict:
    module_preset = account_state.module_presets.get(preset_name, {})
    return {
        'preset_name': preset_name,
        'cards': list(account_state.card_presets.get(preset_name, [])),
        'modules': {
            slot_type: {
                'primary': selection.primary,
                'assist': selection.assist,
            }
            for slot_type, selection in module_preset.items()
        },
        'perks': _perk_selection_payload(account_state, perk_preset_name),
        'bots': {
            'enabled': list(account_state.bots),
            'upgrades': dict(account_state.bot_upgrades),
        },
    }

def _query_response_to_statbook_dict(response, *, bundle_id: str, trace_mode: str) -> dict:
    contributor_rows_by_surface: dict[str, list[dict]] = {}
    for contributor in response.contributor_rows:
        contributor_rows_by_surface.setdefault(contributor.surface_id, []).append({
            'contributor_id': contributor.contributor_id,
            'value': contributor.value,
            'value_type': contributor.value_type,
            'active': contributor.active,
            'gate_reason': contributor.gate_reason,
            'composition_stage': contributor.composition_stage,
            'source_class': contributor.source_class,
            'provenance_ref': contributor.provenance_ref,
        })
    rows = {}
    for resolved in sorted(response.resolved_surface_rows, key=lambda row: row.surface_id):
        rows[resolved.surface_id] = {
            'stat_name': resolved.surface_id,
            'final_value': resolved.final_value,
            'value_type': resolved.value_type,
            'status': resolved.status,
            'contributors': contributor_rows_by_surface.get(resolved.surface_id, []),
            'dependency_trace': list(response.dependency_trace.get(resolved.surface_id, ())),
            'bundle_id': bundle_id,
            'family_id': response.family_id,
            'trace_mode': trace_mode,
        }
    statbook_dict = {
        'rows': rows,
        'diagnostics': {
            'family_id': response.family_id,
            'bundle_id': bundle_id,
            'resolved_surface_count': len(rows),
            'contributor_row_count': len(response.contributor_rows),
            'trace_mode': trace_mode,
        },
    }
    _annotate_display_fields(statbook_dict)
    return statbook_dict

_RUN_STATS_QUERY_OUTPUTS = {
    'start_of_run_rows': 'run_stats_query_rows_start_of_run.json',
    'max_progression_rows': 'run_stats_query_rows_max_progression.json',
    'start_of_run_plan': 'run_stats_query_plan_start_of_run.json',
    'max_progression_plan': 'run_stats_query_plan_max_progression.json',
}

# Legacy output filenames written by pre-T12 run-stats path; deleted on each run.
_RUN_STATS_LEGACY_OUTPUTS = [
    'stat_inputs_start_of_run.json',
    'stat_inputs_max_progression.json',
    'statbook_start_of_run.json',
    'statbook_max_progression.json',
]

def _merge_query_statbooks(*statbook_dicts: dict) -> dict:
    rows: dict[str, dict] = {}
    bundle_ids: list[str] = []
    family_ids: list[str] = []
    contributor_row_count = 0
    for statbook_dict in statbook_dicts:
        diag = statbook_dict.get('diagnostics', {})
        bundle_id = diag.get('bundle_id')
        family_id = diag.get('family_id')
        if bundle_id is not None:
            bundle_ids.append(bundle_id)
        if family_id is not None:
            family_ids.append(family_id)
        contributor_row_count += int(diag.get('contributor_row_count', 0) or 0)
        for surface_id, row in (statbook_dict.get('rows') or {}).items():
            rows[surface_id] = row
    merged = {
        'rows': dict(sorted(rows.items())),
        'diagnostics': {
            'bundle_ids': bundle_ids,
            'family_ids': family_ids,
            'resolved_surface_count': len(rows),
            'contributor_row_count': contributor_row_count,
        },
    }
    _annotate_display_fields(merged)
    return merged

def _extract_tier_number(value) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    digits = ''.join(ch for ch in text if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None

def _run_stats_timing_family_id(*, preset_name: str, perks_enabled: bool) -> str:
    if preset_name == 'Tourney':
        return 'timing_tournament_no_perks'
    if perks_enabled:
        return 'timing_farm_with_perks'
    return 'timing_scenario_probe'

def _run_stats_scenario_config(account_state, *, preset_name: str):
    from simulators.scenario import ScenarioConfig
    if preset_name == 'Tourney':
        league = (
            account_state.player_meta.get('Tourney League')
            or account_state.player_meta.get('Tournament League')
            or account_state.player_meta.get('League')
        )
        return ScenarioConfig(mode_id='tournament', league=league)
    tier = (
        _extract_tier_number(account_state.player_meta.get('Farming Tier'))
        or _extract_tier_number(account_state.highest_tier_unlocked_label)
        or account_state.highest_tier_unlocked_number
        or 14
    )
    return ScenarioConfig(mode_id='farming', tier=int(tier))

def _run_stats_perk_state(account_state, *, preset_name: str, perk_state: str, perk_mode: str, state_mode: str) -> tuple[str | None, bool]:
    if preset_name == 'Tourney':
        return None, False
    current_perk_preset_name = preset_name if preset_name in account_state.perk_presets else None
    current_perks_enabled = _perks_enabled_for_state(current_perk_preset_name, perk_state)
    if state_mode != 'max_progression':
        return current_perk_preset_name, current_perks_enabled
    if perk_mode != 'none' and account_state.active_perk_preset is not None:
        projected_preset_name = account_state.active_perk_preset
        return projected_preset_name, _perks_enabled_for_state(projected_preset_name, perk_state)
    return current_perk_preset_name, current_perks_enabled

def _build_dual_state_stats_view(start_statbook_dict: dict, max_statbook_dict: dict) -> dict:
    start_rows = start_statbook_dict.get('rows', {})
    max_rows = max_statbook_dict.get('rows', {})
    all_keys = sorted(set(start_rows) | set(max_rows))
    rows = {}
    changed_count = 0
    for key in all_keys:
        if key.startswith('raw::'):
            continue
        start_row = start_rows.get(key)
        max_row = max_rows.get(key)
        start_value = None if start_row is None else start_row.get('final_value')
        max_value = None if max_row is None else max_row.get('final_value')
        changed = (
            start_row is None
            or max_row is None
            or start_value != max_value
            or (start_row.get('status') if start_row else None) != (max_row.get('status') if max_row else None)
        )
        if changed:
            changed_count += 1
        rows[key] = {
            'stat_name': key,
            'changed_in_max_progression': changed,
            'start_of_run': None if start_row is None else {
                'final_value': start_value,
                'display_value': start_row.get('display_value'),
                'value_type': start_row.get('value_type'),
                'status': start_row.get('status'),
            },
            'max_progression': None if max_row is None else {
                'final_value': max_value,
                'display_value': max_row.get('display_value'),
                'value_type': max_row.get('value_type'),
                'status': max_row.get('status'),
            },
        }
    return {
        'rows': rows,
        'diagnostics': {
            'row_count': len(rows),
            'changed_in_max_progression_count': changed_count,
        },
    }

def _perk_config_has_active_preset(config: dict) -> bool:
    if not isinstance(config, dict):
        return False
    active = config.get('active_perk_preset')
    presets = config.get('perk_presets') or {}
    return bool(active) and active in presets and bool(presets.get(active))


def _load_perk_entity_registry() -> list[dict]:
    import csv as _csv
    path = ROOT / 'kb' / 'perks' / 'tables' / 'perk-entity-registry.csv'
    rows = []
    with path.open('r', encoding='utf-8-sig', newline='') as fh:
        reader = _csv.DictReader(fh)
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
    metadata.update({
        'resolved_perks_path': 'manual_inputs.yaml:perk_policy',
        'perk_mode': 'max_progression_policy',
        'manual_banned_perk_count': len(banned_names),
    })
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
        (diag_output_dir / 'perk_generation_diagnostics.json').write_text(
            json.dumps(diag, indent=2), encoding='utf-8'
        )
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

def _build_account_state(
    *,
    ids_path: Path,
    manual_inputs_path: Path | None,
    preset: str,
    perk_mode: str,
    diag_output_dir: Path | None = None,
):
    input_bundle = load_inputs(ids_path=ids_path, manual_inputs_path=manual_inputs_path)
    perk_config, perk_config_resolution = _resolve_perk_config(
        perk_mode=perk_mode,
        primary_config=input_bundle.perk_config,
        perk_policy=input_bundle.perk_policy,
        ids_raw=input_bundle.ids_raw,
        diag_output_dir=diag_output_dir,
    )
    account_state = build_runtime_state(
        input_bundle.ids_raw,
        default_preset=preset,
        loadout_config=input_bundle.loadout_config,
        perk_config=perk_config,
    )
    return input_bundle, account_state, perk_config_resolution

def _normalize_perk_mode(perk_mode: str | None) -> str:
    value = str(perk_mode or 'max_progression_policy').strip().lower()
    if value not in {'none', 'max_progression_policy', 'runtime_timeline'}:
        raise ValueError(f'Unsupported perk mode: {perk_mode}')
    return value


def _effective_manual_inputs_path(path: Path | None) -> Path:
    return path if path is not None else ROOT / 'input' / 'manual_inputs.yaml'


def _path_cache_token(path: Path) -> tuple:
    resolved = path.resolve()
    try:
        s = resolved.stat()
        return (str(resolved), s.st_mtime_ns, s.st_size)
    except OSError:
        return (str(resolved), None, None)


class RunStatsSession:
    def __init__(self) -> None:
        self.qe_shared_runtime_context = get_default_qe_shared_runtime_context()
        self.query_kernel = self.qe_shared_runtime_context.query_kernel
        self._account_state_cache: dict[tuple, tuple] = {}

    def _account_state_cache_key(
        self,
        *,
        ids_path: Path,
        manual_inputs_path: Path | None,
        perk_mode: str,
    ) -> tuple:
        return (
            _path_cache_token(ids_path),
            _path_cache_token(_effective_manual_inputs_path(manual_inputs_path)),
            str(perk_mode),
        )

    def get_account_state_bundle(self, *, ids_path: Path, manual_inputs_path: Path | None, perk_mode: str, diag_output_dir: Path | None):
        cache_key = self._account_state_cache_key(
            ids_path=ids_path,
            manual_inputs_path=manual_inputs_path,
            perk_mode=perk_mode,
        )
        cached = self._account_state_cache.get(cache_key)
        if cached is not None:
            return (*cached, True)
        input_bundle, account_state, perk_config_resolution = _build_account_state(
            ids_path=ids_path,
            manual_inputs_path=manual_inputs_path,
            preset='Farming',
            perk_mode=perk_mode,
            diag_output_dir=diag_output_dir,
        )
        cached_value = (input_bundle, account_state, perk_config_resolution)
        self._account_state_cache[cache_key] = cached_value
        return (*cached_value, False)

    def build_run_stats_artifacts(self, args):
        args.perk_state = _normalize_perk_state(args.perk_state)
        args.perk_mode = _normalize_perk_mode(getattr(args, 'perk_mode', None))

        build_start = perf_counter()
        input_bundle, account_state, perk_config_resolution, account_state_cache_hit = self.get_account_state_bundle(
            ids_path=args.ids,
            manual_inputs_path=getattr(args, 'manual_inputs', None),
            perk_mode=args.perk_mode,
            diag_output_dir=args.out / 'diagnostics' / 'perks',
        )
        account_state_build_ms = _elapsed_ms(build_start)

        preset_names = ['Farming', 'Tourney']
        run_stats_payload = {'presets': {}, 'diagnostics': {}}
        preset_diagnostics = {}
        start_books_by_preset = {}
        max_books_by_preset = {}
        state_query_plans = {'start_of_run': {}, 'max_progression': {}}
        pipeline_timings = {'presets': {}}

        for preset_name in preset_names:
            preset_state_timings: dict[str, dict] = {}
            start_perk_preset_name, start_perks_enabled = _run_stats_perk_state(
                account_state,
                preset_name=preset_name,
                perk_state=args.perk_state,
                perk_mode=args.perk_mode,
                state_mode='start_of_run',
            )
            max_perk_preset_name, max_perks_enabled = _run_stats_perk_state(
                account_state,
                preset_name=preset_name,
                perk_state=args.perk_state,
                perk_mode=args.perk_mode,
                state_mode='max_progression',
            )

            for state_mode, perk_preset_name, perks_enabled in (
                ('start_of_run', start_perk_preset_name, start_perks_enabled),
                ('max_progression', max_perk_preset_name, max_perks_enabled),
            ):
                state_start = perf_counter()
                progression_family_id = run_stats_progression_family_id(state_mode=state_mode, perks_enabled=perks_enabled)
                timing_family_id = _run_stats_timing_family_id(preset_name=preset_name, perks_enabled=perks_enabled)
                scenario_config = _run_stats_scenario_config(account_state, preset_name=preset_name)

                t = perf_counter()
                progression_response = resolve_run_stats_progression_bundle(
                    account_state=account_state,
                    family_id=progression_family_id,
                    preset_name=preset_name,
                    perks_enabled=perks_enabled,
                    state_mode=state_mode,
                    perk_preset_name=perk_preset_name,
                    trace_mode='contributors',
                    kernel=self.query_kernel if state_mode == 'start_of_run' else None,
                )
                progression_ms = _elapsed_ms(t)

                t = perf_counter()
                timing_core_response = resolve_timing_consumer_bundle(
                    account_state=account_state,
                    consumer_id='run_stats',
                    bundle_id='timing_core_cycle',
                    family_id=timing_family_id,
                    preset_name=preset_name,
                    scenario_config=scenario_config,
                    perks_enabled=perks_enabled,
                    state_mode=state_mode,
                    perk_preset_name=perk_preset_name,
                    include_optional_surface_ids=('support_surface::timing.gcomp_cooldown_reduction_seconds',),
                    trace_mode='contributors',
                    kernel=self.query_kernel if state_mode == 'start_of_run' else None,
                )
                timing_core_ms = _elapsed_ms(t)

                t = perf_counter()
                timing_wave_response = resolve_timing_consumer_bundle(
                    account_state=account_state,
                    consumer_id='run_stats',
                    bundle_id='timing_wave_duration',
                    family_id=timing_family_id,
                    preset_name=preset_name,
                    scenario_config=scenario_config,
                    perks_enabled=perks_enabled,
                    state_mode=state_mode,
                    perk_preset_name=perk_preset_name,
                    include_optional_surface_ids=(
                        'state::cards.wave_accelerator.spawn_rate_acceleration',
                        'state::tower.package_chance_pct',
                    ),
                    trace_mode='contributors',
                    kernel=self.query_kernel if state_mode == 'start_of_run' else None,
                )
                timing_wave_ms = _elapsed_ms(t)

                t = perf_counter()
                merged_statbook_dict = _merge_query_statbooks(
                    _query_response_to_statbook_dict(
                        progression_response,
                        bundle_id='progression_core_stats',
                        trace_mode='contributors',
                    ),
                    _query_response_to_statbook_dict(
                        timing_core_response,
                        bundle_id='timing_core_cycle',
                        trace_mode='contributors',
                    ),
                    _query_response_to_statbook_dict(
                        timing_wave_response,
                        bundle_id='timing_wave_duration',
                        trace_mode='contributors',
                    ),
                )
                formatting_ms = _elapsed_ms(t)

                if state_mode == 'start_of_run':
                    start_statbook_dict = merged_statbook_dict
                else:
                    max_statbook_dict = merged_statbook_dict

                state_query_plans[state_mode][preset_name] = {
                    'progression': {
                        'bundle_id': 'progression_core_stats',
                        'family_id': progression_family_id,
                        'resolved_surface_ids': [row.surface_id for row in progression_response.resolved_surface_rows],
                    },
                    'timing': [
                        {
                            'bundle_id': 'timing_core_cycle',
                            'family_id': timing_family_id,
                            'resolved_surface_ids': [row.surface_id for row in timing_core_response.resolved_surface_rows],
                        },
                        {
                            'bundle_id': 'timing_wave_duration',
                            'family_id': timing_family_id,
                            'resolved_surface_ids': [row.surface_id for row in timing_wave_response.resolved_surface_rows],
                        },
                    ],
                }
                preset_state_timings[state_mode] = {
                    'resolve_progression_ms': progression_ms,
                    'resolve_timing_core_ms': timing_core_ms,
                    'resolve_timing_wave_ms': timing_wave_ms,
                    'publication_ms': 0.0,
                    'formatting_ms': formatting_ms,
                    'total_state_ms': _elapsed_ms(state_start),
                }

            dual_state_stats = _build_dual_state_stats_view(start_statbook_dict, max_statbook_dict)
            run_stats_payload['presets'][preset_name] = {
                'loadout': {
                    'start_of_run': _preset_loadout_summary(
                        account_state,
                        preset_name=preset_name,
                        perk_preset_name=start_perk_preset_name,
                    ),
                    'max_progression': _preset_loadout_summary(
                        account_state,
                        preset_name=preset_name,
                        perk_preset_name=max_perk_preset_name,
                    ),
                },
                'stats': dual_state_stats,
            }
            preset_diagnostics[preset_name] = {
                'start_of_run': {
                    'query_backend': 'bounded_qe_bundle',
                    'statbook_row_count': len(start_statbook_dict.get('rows', {})),
                    'bundle_ids': start_statbook_dict.get('diagnostics', {}).get('bundle_ids', []),
                    'family_ids': start_statbook_dict.get('diagnostics', {}).get('family_ids', []),
                    'resolved_surface_count': start_statbook_dict.get('diagnostics', {}).get('resolved_surface_count'),
                    'contributor_row_count': start_statbook_dict.get('diagnostics', {}).get('contributor_row_count'),
                    'timings_ms': preset_state_timings['start_of_run'],
                },
                'max_progression': {
                    'query_backend': 'bounded_qe_bundle',
                    'statbook_row_count': len(max_statbook_dict.get('rows', {})),
                    'bundle_ids': max_statbook_dict.get('diagnostics', {}).get('bundle_ids', []),
                    'family_ids': max_statbook_dict.get('diagnostics', {}).get('family_ids', []),
                    'resolved_surface_count': max_statbook_dict.get('diagnostics', {}).get('resolved_surface_count'),
                    'contributor_row_count': max_statbook_dict.get('diagnostics', {}).get('contributor_row_count'),
                    'timings_ms': preset_state_timings['max_progression'],
                },
                'dual_state_stats': dual_state_stats.get('diagnostics', {}),
            }
            start_books_by_preset[preset_name] = start_statbook_dict
            max_books_by_preset[preset_name] = max_statbook_dict
            pipeline_timings['presets'][preset_name] = preset_state_timings

        diagnostics = {
            'pipeline_kind': 'stats',
            'query_backend': 'bounded_qe_bundle',
            'preset_names': preset_names,
            'state_modes': ['start_of_run', 'max_progression'],
            'perk_state': args.perk_state,
            'perk_mode': args.perk_mode,
            'perk_config_resolution': perk_config_resolution,
            'qe_shared_runtime_context': self.qe_shared_runtime_context.to_dict(),
            'session': {
                'kind': 'run_stats_session',
                'account_state_cache_hit': account_state_cache_hit,
                'account_state_build_ms': account_state_build_ms,
            },
            'presets': preset_diagnostics,
            'query_plans': state_query_plans,
            'timings_ms': pipeline_timings,
        }
        run_stats_payload['diagnostics'] = diagnostics
        return {
            'run_stats_payload': run_stats_payload,
            'diagnostics': diagnostics,
            'account_state': account_state,
            'start_books_by_preset': start_books_by_preset,
            'max_books_by_preset': max_books_by_preset,
            'state_query_plans': state_query_plans,
        }

    def execute(self, args) -> int:
        args.out.mkdir(parents=True, exist_ok=True)
        _remove_run_stats_legacy_outputs(args.out)
        artifacts = self.build_run_stats_artifacts(args)
        diagnostics = artifacts['diagnostics']
        write_start = perf_counter()
        (args.out / 'account_state.json').write_text(
            json.dumps(_json_sanitize(_sanitized_account_state_for_output(artifacts['account_state'], 'Farming')), indent=2, default=str)
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['start_of_run_plan']).write_text(
            json.dumps(_json_sanitize({
                'pipeline_kind': 'run_stats_bounded_query',
                'state_mode': 'start_of_run',
                'presets': artifacts['state_query_plans']['start_of_run'],
            }), indent=2, default=str)
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['max_progression_plan']).write_text(
            json.dumps(_json_sanitize({
                'pipeline_kind': 'run_stats_bounded_query',
                'state_mode': 'max_progression',
                'presets': artifacts['state_query_plans']['max_progression'],
            }), indent=2, default=str)
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['start_of_run_rows']).write_text(json.dumps(_json_sanitize(artifacts['start_books_by_preset']), indent=2, default=str))
        (args.out / _RUN_STATS_QUERY_OUTPUTS['max_progression_rows']).write_text(json.dumps(_json_sanitize(artifacts['max_books_by_preset']), indent=2, default=str))
        (args.out / 'run_stats.json').write_text(json.dumps(_json_sanitize(artifacts['run_stats_payload']), indent=2, default=str))
        diagnostics['timings_ms']['write_outputs_ms'] = _elapsed_ms(write_start)
        (args.out / 'diagnostics.json').write_text(json.dumps(_json_sanitize(diagnostics), indent=2, default=str))
        return 0

@lru_cache(maxsize=1)
def get_default_run_stats_session() -> RunStatsSession:
    return RunStatsSession()

def run_stats_pipeline(args) -> int:
    return get_default_run_stats_session().execute(args)

def run_stats_watch_loop(args) -> int:
    session = get_default_run_stats_session()
    print("run_stats watch mode is warm. Press Enter to rerun, or type 'q' to quit.")
    while True:
        rc = session.execute(args)
        if rc != 0: return rc
        try: user_input = input("run_stats watch > ").strip().lower()
        except EOFError: return 0
        if user_input in {'q', 'quit', 'exit'}: return 0

def _run_stats_request_payload(args) -> dict[str, object]:
    return {
        'ids': str(args.ids),
        'out': str(args.out),
        'manual_inputs': str(getattr(args, 'manual_inputs', None)) if getattr(args, 'manual_inputs', None) is not None else None,
        'perk_mode': getattr(args, 'perk_mode', 'none'),
        'perk_state': getattr(args, 'perk_state', 'auto'),
    }

def _run_stats_args_from_payload(payload: dict[str, object]):
    return SimpleNamespace(
        ids=Path(str(payload['ids'])),
        out=Path(str(payload['out'])),
        manual_inputs=Path(str(payload['manual_inputs'])) if payload.get('manual_inputs') else None,
        perk_mode=str(payload.get('perk_mode', 'none')),
        perk_state=str(payload.get('perk_state', 'auto')),
    )

def run_stats_server(args) -> int:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    session = get_default_run_stats_session()
    server_address = (getattr(args, 'host', '127.0.0.1'), int(getattr(args, 'port', 8765)))
    class _RunStatsHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            if self.path != '/run': self.send_error(404); return
            content_length = int(self.headers.get('Content-Length', '0'))
            payload = json.loads(self.rfile.read(content_length).decode('utf-8'))
            request_args = _run_stats_args_from_payload(payload)
            rc = session.execute(request_args)
            body = json.dumps({'ok': rc == 0, 'exit_code': rc, 'out': str(request_args.out)}).encode('utf-8')
            self.send_response(200 if rc == 0 else 500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self) -> None:
            if self.path != '/health': self.send_error(404); return
            body = json.dumps({'ok': True}).encode('utf-8')
            self.send_response(200); self.end_headers(); self.wfile.write(body)
        def log_message(self, format: str, *args) -> None: return
    with ThreadingHTTPServer(server_address, _RunStatsHandler) as server:
        try: server.serve_forever()
        except KeyboardInterrupt: return 0
    return 0

def run_stats_client(args) -> int:
    from urllib import request as urllib_request
    url = f"http://{getattr(args, 'host', '127.0.0.1')}:{int(getattr(args, 'port', 8765))}/run"
    request_body = json.dumps(_run_stats_request_payload(args)).encode('utf-8')
    req = urllib_request.Request(url, data=request_body, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib_request.urlopen(req, timeout=60) as response:
            payload = json.loads(response.read().decode('utf-8'))
            print(json.dumps(payload, indent=2))
            return int(payload.get('exit_code', 1))
    except Exception as exc: print(f"run_stats client failed: {exc}"); return 1

def run_stats_local_server_is_healthy(args, *, timeout_seconds: float = 0.25) -> bool:
    from urllib import request as urllib_request
    url = f"http://{getattr(args, 'host', '127.0.0.1')}:{int(getattr(args, 'port', 8765))}/health"
    try:
        with urllib_request.urlopen(url, timeout=timeout_seconds) as response:
            return bool(json.loads(response.read().decode('utf-8')).get('ok'))
    except: return False

def run_stats_ensure_local_server(args) -> bool:
    import subprocess, time
    if run_stats_local_server_is_healthy(args): return True
    command = [sys.executable, '-m', 'app.run_stats', '--server']
    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        if run_stats_local_server_is_healthy(args): return True
        time.sleep(0.1)
    return False

def run_analysis_pipeline(args) -> int:
    args.state_mode = normalize_state_mode(args.state_mode)
    args.perk_state = _normalize_perk_state(args.perk_state)
    args.perk_mode = _normalize_perk_mode(getattr(args, 'perk_mode', None))
    args.out.mkdir(parents=True, exist_ok=True)

    _input_bundle = load_inputs(ids_path=args.ids, manual_inputs_path=getattr(args, 'manual_inputs', None))
    ids_raw = _input_bundle.ids_raw
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
    qe_planner = QEResolutionPlanner()

    _ep_kwargs = dict(
        ep_stage_context_for_destination=_ep_stage_context_for_destination,
        compare_state_key_for_destination=_compare_state_key_for_destination,
        contributor_snapshot=_contributor_snapshot,
        apply_projected_runtime_compare_assumptions=_apply_projected_runtime_compare_assumptions,
        formula_contract=_formula_contract,
        normalize_compare_values=_normalize_compare_values,
    )

    (account_state, compare_rows_by_preset, compare_publishable_rows_by_preset, package_stage_context) = _build_compare_rows_by_preset(
        ids_raw=ids_raw, loadout_config=loadout_config, perk_config=perk_config,
        formula_ledger=formula_ledger, state_mode=args.state_mode, default_preset=args.preset,
        ep_oracle=ep_oracle, perk_state=args.perk_state, snapshot_planner=qe_planner,
    )

    perks_enabled = _perks_enabled_for_state(account_state.active_perk_preset, args.perk_state)
    main_snapshot = qe_planner.resolve_report_snapshot(
        account_state, preset_name=args.preset, state_mode=args.state_mode, perks_enabled=perks_enabled,
    )
    stat_inputs = list(main_snapshot.stat_inputs)
    statbook = main_snapshot.statbook
    _merge_scenario_publication_rows(
        statbook,
        account_state=account_state,
        stat_inputs=stat_inputs,
        preset_name=args.preset,
        state_mode=args.state_mode,
        perks_enabled=perks_enabled,
        manual_advisory_inputs=_input_bundle.manual_advisory_inputs,
    )
    publish_query_surfaces(
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

    state_matrix: dict[str, object] = {}
    for state_mode in SUPPORTED_STATE_MODES:
        matrix_snapshot = qe_planner.resolve_report_snapshot(
            account_state, preset_name=args.preset, state_mode=state_mode, perks_enabled=perks_enabled,
        )
        matrix_inputs = list(matrix_snapshot.stat_inputs)
        matrix_statbook_obj = matrix_snapshot.statbook
        _merge_scenario_publication_rows(
            matrix_statbook_obj,
            account_state=account_state,
            stat_inputs=matrix_inputs,
            preset_name=args.preset,
            state_mode=state_mode,
            perks_enabled=perks_enabled,
            manual_advisory_inputs=_input_bundle.manual_advisory_inputs,
        )
        publish_query_surfaces(
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

    ep_compare = build_ep_compare(
        ep_oracle, compare_rows_by_preset, formula_ledger, package_stage_context, **_ep_kwargs
    )
    ep_compare_publishable = build_ep_compare(
        ep_oracle, compare_publishable_rows_by_preset, formula_ledger, package_stage_context, **_ep_kwargs
    )
    _annotate_compare_display_fields(ep_compare)
    _annotate_compare_display_fields(ep_compare_publishable)
    current_compare_summary = build_compare_status_summary(ep_compare_publishable)

    ep_compare_publishable = _ensure_compare_authoritative_verdict_fields(ep_compare_publishable)
    line_verification = build_line_by_line_verification(
        statbook_publishable_dict, ep_compare_publishable, formula_ledger, _formula_contract
    )
    line_verification = _ensure_line_verification_authoritative_verdict_fields(line_verification)
    survivor_report = build_survivor_closure_report(ep_compare_publishable, line_verification)

    optimizer_scores = compute_optimizer_scores(statbook_dict)
    audit_surface_manifest = _build_audit_surface_manifest(account_state, args.preset)
    artifact_contract_manifest = _build_artifact_contract_manifest(account_state, args.preset, stat_inputs, statbook_dict)
    family_completeness_matrix = _build_family_completeness_matrix(account_state, stat_inputs)

    audits = _build_publish_gate_audits(stat_inputs, statbook_publishable_dict, ep_compare_publishable, formula_ledger)
    kb_incomplete_areas = _build_kb_incomplete_areas(stat_inputs, statbook_publishable_dict, formula_ledger)
    kb_gap_register = _build_kb_gap_register(kb_incomplete_areas, audits)

    routed_input_count = sum(1 for r in stat_inputs if r.destination_id)
    truly_unrouted_input_count = sum(1 for r in stat_inputs if not r.destination_id)
    resolved_surface_count = statbook.diagnostics.get('resolved_stat_count', 0)
    partial_surface_count = statbook.diagnostics.get('partially_resolved_stat_count', 0)
    total_input_count = len(stat_inputs)

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
        'stat_input_count': total_input_count,
        'statbook_row_count': len(statbook.rows),
        'engine_status': statbook.diagnostics.get('resolver_status'),
        'qe_resolution_interface': statbook.diagnostics.get('qe_resolution_interface'),
        'qe_resolution_backend': statbook.diagnostics.get('qe_resolution_backend'),
        'publish_status': statbook_publishable_dict.get('diagnostics', {}).get('oracle_policy'),
        'formula_ledger_version': formula_ledger.get('version'),
        'mapped_stat_input_count': routed_input_count,
        'unmapped_stat_input_count': truly_unrouted_input_count,
        'resolved_stat_count': resolved_surface_count,
        'partially_resolved_stat_count': partial_surface_count,
        'ep_compare_summary': current_compare_summary,
        **current_compare_summary,
        'active_perk_preset': _sanitized_active_perk_preset(account_state, args.preset),
        'configured_perk_presets': _sanitized_configured_perk_presets(account_state, args.preset),
        'active_card_preset': account_state.active_card_preset,
        'active_module_preset': account_state.active_module_preset,
        'perk_state': args.perk_state,
        'kb_incomplete_areas': kb_incomplete_areas,
        'kb_gap_register': kb_gap_register,
        'audits': audits,
        'timings_ms': {},
    }
    diagnostics['tower_regen_closure_report'] = _build_tower_regen_closure_report(ep_compare_publishable)
    diagnostics['tower_hp_semantic_gap_report'] = _build_tower_hp_semantic_gap_report(ep_compare_publishable)
    diagnostics['tower_damage_residue_analysis'] = _build_tower_damage_residue_analysis(ep_compare_publishable)

    write_core_outputs(
        out_dir=args.out,
        diagnostics=diagnostics,
        account_state_payload=_sanitized_account_state_for_output(account_state, args.preset),
        stat_inputs_payload=[row.to_dict() for row in stat_inputs],
        statbook_dict=statbook_dict,
        statbook_publishable_dict=statbook_publishable_dict,
        ep_compare_publishable=ep_compare_publishable,
        line_verification=line_verification,
        survivor_closure_report=survivor_report,
        state_matrix=state_matrix,
        optimizer_scores=optimizer_scores,
        audit_surface_manifest=audit_surface_manifest,
        artifact_contract_manifest=artifact_contract_manifest,
        family_completeness_matrix=family_completeness_matrix,
        root_path=ROOT,
    )
    return 0

def run_pipeline(args) -> int:
    return run_analysis_pipeline(args)

def _load_json_artifact(path: Path) -> dict[str, object]:
    if not path.exists(): return {}
    try: return json.loads(path.read_text(encoding='utf-8'))
    except: return {}

def _generated_output_paths(out_dir: Path) -> list[Path]:
    return sorted(out_dir.glob('*.json')) + sorted(out_dir.glob('*.csv'))

def _remove_run_stats_legacy_outputs(out_dir: Path) -> None:
    for name in _RUN_STATS_LEGACY_OUTPUTS:
        path = out_dir / name
        if path.exists():
            path.unlink()


def _build_pipeline_trace_from_artifacts(
    *,
    request: PipelineRunRequest,
    total_elapsed_ms: float,
    diagnostics: dict[str, object],
) -> PipelineTrace:
    execution_path = {
        'recompute_mode': diagnostics.get('qe_resolution_backend') or diagnostics.get('query_backend') or 'analysis_pipeline',
        'execution_branch': diagnostics.get('qe_resolution_interface') or diagnostics.get('pipeline_kind') or 'analysis_pipeline',
        'cache_status': 'warm' if ((diagnostics.get('session') or {}).get('account_state_cache_hit')) else 'cold',
        'fallback_required': False,
        'fallback_reason': None,
        'bundle_used': None,
        'consumer_id': None,
        'family_id': diagnostics.get('qe_native_family_id'),
        'runtime_consumers': [],
        'cache_fingerprint': None,
        'cache_validation': None,
        'incremental_plan': None,
        'parity': None,
        'runtime_publication': None,
        'total_elapsed_ms': total_elapsed_ms,
    }
    timings = diagnostics.get('timings_ms') or {}
    stages = [
        PipelineStageRecord(
            stage_id='input_load',
            title='Input load',
            owner_module='input.loader',
            entry_function='load_inputs',
            status='ok',
            elapsed_ms=float(((diagnostics.get('session') or {}).get('account_state_build_ms')) or 0.0),
            outputs_summary={'section_names': diagnostics.get('section_names', []), 'section_row_counts': diagnostics.get('section_row_counts', {})},
        ),
        PipelineStageRecord(
            stage_id='runtime_account_assembly',
            title='Runtime/account assembly',
            owner_module='input.runtime_state',
            entry_function='build_runtime_state',
            status='ok',
            elapsed_ms=float(((diagnostics.get('session') or {}).get('account_state_build_ms')) or 0.0),
            outputs_summary={'perk_config_resolution': diagnostics.get('perk_config_resolution', {}), 'perk_support': diagnostics.get('perk_support', {})},
        ),
        PipelineStageRecord(
            stage_id='compare_materialization',
            title='Compare materialization',
            owner_module='evaluators.compare',
            entry_function='_build_compare_rows_by_preset',
            status='ok',
            elapsed_ms=0.0,
            outputs_summary={
                'default_preset': diagnostics.get('default_preset'),
                'state_mode': diagnostics.get('state_mode'),
                'perk_state': diagnostics.get('perk_support', {}).get('perk_state'),
            },
        ),
        PipelineStageRecord(
            stage_id='stat_resolution',
            title='Stat-input compilation and resolution',
            owner_module='qe.routing',
            entry_function='QEResolutionPlanner.resolve_report_snapshot',
            status='ok',
            elapsed_ms=float((((timings.get('presets') or {}).get(request.preset, {}) or {}).get(request.state_mode, {}) or {}).get('total_state_ms', 0.0)),
            outputs_summary={
                'stat_input_count': diagnostics.get('stat_input_count'),
                'statbook_row_count': diagnostics.get('statbook_row_count'),
                'engine_status': diagnostics.get('engine_status'),
                'qe_resolution_backend': diagnostics.get('qe_resolution_backend'),
            },
        ),
        PipelineStageRecord(
            stage_id='checks_generation',
            title='Compare/verification generation',
            owner_module='evaluators.compare',
            entry_function='build_line_by_line_verification',
            status='ok',
            elapsed_ms=0.0,
            outputs_summary={
                'ep_compare_summary': diagnostics.get('ep_compare_summary', {}),
                'state_matrix_modes': list((diagnostics.get('state_matrix') or {}).keys()),
            },
        ),
        PipelineStageRecord(
            stage_id='artifact_write',
            title='Artifact write',
            owner_module='app.pipeline',
            entry_function='write_core_outputs',
            status='ok',
            elapsed_ms=float(timings.get('write_outputs_ms') or 0.0),
            outputs_summary={'out_dir': _relpath_str(request.out)},
        ),
    ]
    return PipelineTrace(
        request={
            'ids': _relpath_str(request.ids),
            'out': _relpath_str(request.out),
            'preset': request.preset,
            'state_mode': request.state_mode,
            'manual_inputs': None if request.manual_inputs is None else _relpath_str(request.manual_inputs),
            'perk_mode': request.perk_mode,
            'include_slow_audits': request.include_slow_audits,
            'perk_state': request.perk_state,
        },
        execution_path=execution_path,
        stages=stages,
        artifacts_written=[],
    )

def execute_pipeline(request: PipelineRunRequest) -> PipelineRunResult:
    started_at = perf_counter()
    args = SimpleNamespace(
        ids=request.ids, out=request.out, preset=request.preset, 
        state_mode=request.state_mode, manual_inputs=request.manual_inputs,
        perk_mode=request.perk_mode, include_slow_audits=request.include_slow_audits,
        perk_state=request.perk_state
    )
    exit_code = run_analysis_pipeline(args)
    total_elapsed_ms = _elapsed_ms(started_at)
    diagnostics = _load_json_artifact(request.out / 'diagnostics.json')
    generated_files = _generated_output_paths(request.out)
    trace = _build_pipeline_trace_from_artifacts(request=request, total_elapsed_ms=total_elapsed_ms, diagnostics=diagnostics)
    trace = PipelineTrace(
        request=trace.request, execution_path=trace.execution_path,
        stages=trace.stages, artifacts_written=[_relpath_str(p) for p in generated_files]
    )
    write_pipeline_trace(request.out, trace, ROOT)
    generated_files = _generated_output_paths(request.out)
    return PipelineRunResult(exit_code, request, request.out, diagnostics, tuple(generated_files), trace)

def build_verification_snapshot_set(
    base_request: PipelineRunRequest,
    specs: tuple[VerificationSnapshotSpec, ...] | None = None,
) -> list[PipelineRunResult]:
    if specs is None:
        specs = (
            VerificationSnapshotSpec('Farming', 'start_of_run'),
            VerificationSnapshotSpec('Farming', 'max_progression'),
            VerificationSnapshotSpec('Tourney', 'start_of_run', perk_state='off'),
            VerificationSnapshotSpec('Tourney', 'max_progression', perk_state='off'),
        )
    results = []
    for spec in specs:
        out_dir = base_request.out / (spec.out_subdir or f'{spec.preset.lower()}_{spec.state_mode}')
        req = PipelineRunRequest(
            ids=base_request.ids, out=out_dir, preset=spec.preset,
            state_mode=spec.state_mode, manual_inputs=base_request.manual_inputs,
            perk_mode=base_request.perk_mode, include_slow_audits=base_request.include_slow_audits,
            perk_state=spec.perk_state,
        )
        results.append(execute_pipeline(req))
    return results

def resolve_fast_checkpoint(request: FastCheckpointRequest) -> FastCheckpointResult:
    if not request.requested_surface_ids:
        raise ValueError('FastCheckpointRequest.requested_surface_ids must be non-empty')
    _, account_state, _ = _build_account_state(
        ids_path=request.ids, manual_inputs_path=request.manual_inputs,
        preset=request.preset, perk_mode=request.perk_mode,
    )
    perks_enabled = _perks_enabled_for_state(account_state.active_perk_preset, request.perk_state)
    checkpoint_resolution = SimulatorSnapshotResolver().resolve_checkpoint(
        account_state=account_state,
        checkpoint_state=SimulatorCheckpointState(),
        preset_name=request.preset,
        requested_surface_ids=request.requested_surface_ids,
        state_mode=request.state_mode,
        card_preset_name=account_state.active_card_preset,
        module_preset_name=account_state.active_module_preset,
        perk_preset_name=account_state.active_perk_preset,
        perks_enabled=perks_enabled,
    )
    response = resolve_checkpoint_surfaces(
        account_state,
        requested_surface_ids=request.requested_surface_ids,
        preset_name=request.preset,
        state_mode=request.state_mode,
        card_preset_name=account_state.active_card_preset,
        module_preset_name=account_state.active_module_preset,
        perk_preset_name=account_state.active_perk_preset,
        perks_enabled=perks_enabled,
        trace_mode='contributors',
    )
    statbook = query_response_to_statbook(
        response,
        notes='Lightweight QE checkpoint resolution for interactive stat verification.',
        diagnostics={
            'resolver_kind': checkpoint_resolution.diagnostics.get('resolver_kind'),
            'phase_timing_ms': checkpoint_resolution.diagnostics.get('phase_timing_ms'),
            'requested_surface_ids': list(request.requested_surface_ids),
            'state_mode': request.state_mode,
            'preset': request.preset,
            'perk_state': request.perk_state,
        },
    )
    statbook_dict = statbook.to_dict()
    _annotate_display_fields(statbook_dict)
    return FastCheckpointResult(
        request=request,
        statbook=statbook_dict,
        diagnostics=dict(checkpoint_resolution.diagnostics),
    )
