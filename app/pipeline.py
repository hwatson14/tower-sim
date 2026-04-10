"""
app/pipeline.py -- Layer wiring.

Owns: wiring input -> qe -> simulators -> evaluators -> advisors,
output assembly, pipeline configuration.
Must not own: domain logic.

T12: bridge removed; all _h.* calls resolved to real owners.
Domain helpers live in their real owners (evaluators.compare, input.loader).
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Active layer imports
from qe.stat_input_compiler import (
    PERK_TARGET_DESTINATION_OVERRIDES,
    TRADE_OFF_BENEFIT_EFFECT_INDEXES,
    compile_stat_inputs,
    load_card_base_value_display_map,
    load_card_effect_display_names,
    load_card_mastery_values,
    load_perk_effects,
    load_perk_entities,
    load_perk_entity_rows,
    normalize_state_mode,
    scaled_perk_value,
    SUPPORTED_STATE_MODES,
    state_mode_support,
)
from app.models import (
    PipelineRunRequest,
    PipelineStageRecord,
    PipelineTrace,
    PipelineRunResult,
    VerificationSnapshotSpec,
    FastCheckpointRequest,
    FastCheckpointResult,
    _normalize_perk_state,
)
from app.publication import (
    RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS,
    RUN_STATS_COMMITTED_BASELINE_ARTIFACTS,
    RUN_STATS_LOCAL_SUPPORT_ARTIFACTS,
    _build_input_dashboard_payload,
    _build_stats_dashboard_payload,
    _remove_legacy_outputs,
    _RUN_STATS_LEGACY_OUTPUTS,
    _json_sanitize,
    _relpath_str,
    _load_json_artifact,
    _generated_output_paths,
    write_core_outputs,
    write_pipeline_trace,
)
from app.display import (
    annotate_compare_display_fields as _annotate_compare_display_fields,
    annotate_display_fields as _annotate_display_fields,
)
from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from qe.contracts import (
    normalize_surface_id_to_contract,
    normalize_contract_payload,
    sanitize_perk_presets_for_canonical_output,
    sanitize_preset_name_for_canonical_output,
)
from qe.publication import build_input_dashboard_qe_publications as qe_build_input_dashboard_qe_publications, publish_query_surfaces
from qe.routing import QEResolutionPlanner, query_response_to_statbook, resolve_checkpoint_surfaces
from qe.shared_runtime_context import get_default_qe_shared_runtime_context
from qe.query_module_policy import build_module_card_payloads, load_module_substat_lookup
from simulators.progression import resolve_run_stats_progression_bundle
from simulators.contracts import SimulatorCheckpointState
from simulators.perk_timeline_generator import (
    PerkTimelinePolicy,
    generate_timeline_from_policy,
    perk_state_at_wave,
)
from simulators.snapshot_resolver import SimulatorSnapshotResolver
from simulators.timing import compile_timing_family_rows, merge_scenario_publication_rows as merge_timing_scenario_publication_rows, resolve_timing_consumer_bundle
from simulators.contracts import PerkState
from simulators.run_executor import RunToMaxConfig, build_boss_wave_table_payload, build_start_of_run_state
from input.state_types import ScenarioRuntimeInputs
from qe.models import BoundStatInputs, bind_state_identity


def _load_json_config(path: Path) -> dict:
    import json
    return json.loads(path.read_text(encoding='utf-8'))


def _safe_pct(n: int, d: int) -> float:
    return round((100.0 * n / d), 2) if d else 0.0


def _build_input_dashboard_qe_publications(
    *,
    account_state,
    compare_rows_by_preset: dict[str, dict],
    projected_compare_rows_by_preset: dict[str, dict],
    stat_inputs: list,
    preset_name: str,
) -> dict[str, object]:
    return qe_build_input_dashboard_qe_publications(
        account_state=account_state,
        compare_rows_by_preset=compare_rows_by_preset,
        projected_compare_rows_by_preset=projected_compare_rows_by_preset,
        stat_inputs=stat_inputs,
        preset_name=preset_name,
    )


def _contract_json_payload(obj):
    return normalize_contract_payload(_json_sanitize(obj))


def load_streamlit_reference_data(*, ids_path: Path, manual_inputs_path: Path | None) -> dict[str, object]:
    bundle = load_inputs(ids_path=ids_path, manual_inputs_path=manual_inputs_path)
    perk_policy = bundle.perk_policy or {}
    manual_banned_names = set(_resolve_manual_banned_perks(perk_policy))
    perk_entity_map = load_perk_entities()
    by_name = {str(row.get('perk_name') or '').strip(): perk_id for perk_id, row in perk_entity_map.items()}
    manual_banned_perk_ids = {by_name[name] for name in manual_banned_names if name in by_name}

    return {
        'card_effects': load_card_effect_display_names(),
        'card_values': load_card_base_value_display_map(),
        'card_mastery_values': load_card_mastery_values(),
        'perk_entity_map': perk_entity_map,
        'perk_entities': perk_entity_map,
        'perk_effects': load_perk_effects(),
        'manual_banned_perk_ids': manual_banned_perk_ids,
        'module_substat_lookup': load_module_substat_lookup(),
    }


def compute_perk_max_effect_displays(
    *,
    perk_id: str,
    standard_bonus_pct: float | None,
    tradeoff_bonus_pct: float | None,
) -> list[tuple[object, object]]:
    perk_entities = load_perk_entities()
    perk_effects = load_perk_effects()
    perk_meta = perk_entities.get(perk_id) or {}
    max_picks = int(perk_meta.get('max_picks') or 0)
    perk_lab_state = {
        'standard_bonus_multiplier': 1.0 + (((standard_bonus_pct or 0.0) / 100.0)),
        'tradeoff_bonus_multiplier': 1.0 + (((tradeoff_bonus_pct or 0.0) / 100.0)),
    }
    rows: list[tuple[object, object]] = []
    for effect in (perk_effects.get(perk_id) or []):
        scaled = scaled_perk_value(
            perk_meta=perk_meta,
            perk_effect_meta=effect,
            perk_id=perk_id,
            operation=str(effect.get('operation') or '').strip(),
            raw_value=str(effect.get('effect_value') or '').strip(),
            picks=max_picks,
            effect_index=str(effect.get('effect_index') or '').strip(),
            perk_lab_state=perk_lab_state,
        )
        rows.append((scaled, effect.get('operation')))
    return rows


def build_boss_wave_payload(
    request: PipelineRunRequest,
    *,
    preset_name: str,
    tier_number: int,
    end_wave: int,
    boss_wave_step: int,
    stop_on_failure: bool,
    scenario_runtime_inputs: dict[str, float],
) -> dict[str, object]:
    bundle = load_inputs(ids_path=request.ids, manual_inputs_path=request.manual_inputs)
    account_state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    initial_state = build_start_of_run_state(
        account_state,
        preset_name=preset_name,
        perk_state=PerkState(wave=0, counts={}, dirty=False),
    )
    config = RunToMaxConfig(
        execution_mode='table_sweep',
        preset_name=preset_name,
        tier_column=f'Tier {int(tier_number)}',
        start_wave=max(1, int(boss_wave_step)),
        end_wave=int(end_wave),
        boss_wave_step=int(boss_wave_step),
        state_mode='start_of_run',
        scenario_runtime_inputs=ScenarioRuntimeInputs.from_mapping(scenario_runtime_inputs),
    )
    boss_wave_run = build_boss_wave_table_payload(
        account_state=account_state,
        initial_projected_state=initial_state,
        config=config,
        stop_on_failure=bool(stop_on_failure),
    )
    rows = list(boss_wave_run.get('rows') or [])
    summary = dict(boss_wave_run.get('summary') or {})
    execution_diagnostics = dict(boss_wave_run.get('diagnostics') or {})
    return {
        'artifact': 'boss_wave_dashboard_payload',
        'schema_version': 1,
        'contract': {
            'payload_owner': 'app.pipeline.build_boss_wave_payload',
            'simulator_owner': 'simulators.run_executor.build_boss_wave_table_payload',
            'row_output_kind': 'boss_wave_table_rows',
            'summary_kind': 'max_wave_survivability',
            'checkpoint_mode': 'boss_wave_only',
        },
        'rows': rows,
        'summary': {
            'preset_name': preset_name,
            'tier_column': config.tier_column,
            'state_mode': config.state_mode,
            'max_wave': int(summary.get('max_wave') or 0),
            'max_surviving_wave': int(summary.get('max_surviving_wave') or 0),
            'first_failed_wave': int(summary.get('first_failed_wave') or 0),
            'row_count': int(summary.get('row_count') or len(rows)),
            'terminal_display_wave': int(summary.get('terminal_display_wave') or 0),
            'survives_through_end': bool(summary.get('survives_through_end')),
            'result_consistent_with_rows': bool(summary.get('result_consistent_with_rows')),
        },
        'diagnostics': {
            'preset_name': preset_name,
            **execution_diagnostics,
        },
        'download': {
            'format': 'csv',
            'file_name': f'{preset_name.lower()}_tier_{int(tier_number)}_boss_waves.csv',
        },
    }



def _published_statbook_dict(statbook, *, manual_advisory_inputs: dict, account_state_labs: dict) -> dict:
    from qe.publication import publish_query_surfaces

    publish_query_surfaces(
        statbook.rows,
        manual_advisory_inputs=manual_advisory_inputs,
        account_state_labs=account_state_labs,
    )
    statbook_dict = statbook.to_dict()
    _annotate_display_fields(statbook_dict)
    return statbook_dict


def _annotate_compare_row_payloads_by_preset(rows_by_preset: dict[str, dict]) -> None:
    for rows in (rows_by_preset or {}).values():
        payload = {'rows': rows}
        _annotate_display_fields(payload)


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
    merge_timing_scenario_publication_rows(
        statbook,
        account_state=account_state,
        stat_inputs=stat_inputs,
        family_id=timing_family_id,
        preset_name=preset_name,
        scenario_config=scenario_config,
        state_mode=state_mode,
        perks_enabled=perks_enabled,
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


def _query_response_to_statbook_dict(
    response,
    *,
    bundle_id: str,
    trace_mode: str,
    manual_advisory_inputs: dict | None = None,
    account_state_labs: dict | None = None,
    publish_qe_surfaces: bool = False,
) -> dict:
    statbook = query_response_to_statbook(
        response,
        notes='Resolved through run_stats bounded query bundle.',
        diagnostics={
            'bundle_id': bundle_id,
            'resolved_surface_count': len(response.resolved_surface_rows),
            'contributor_row_count': len(response.contributor_rows),
            'trace_mode': trace_mode,
        },
    )
    if publish_qe_surfaces:
        publish_query_surfaces(
            statbook.rows,
            manual_advisory_inputs=manual_advisory_inputs,
            account_state_labs=account_state_labs,
        )
    statbook_dict = statbook.to_dict()
    for surface_id, row in (statbook_dict.get('rows') or {}).items():
        row['stat_name'] = surface_id
        row['bundle_id'] = bundle_id
        row['family_id'] = response.family_id
        row['trace_mode'] = trace_mode
    statbook_dict['diagnostics'] = {
        **dict(statbook_dict.get('diagnostics') or {}),
        'family_id': response.family_id,
        'bundle_id': bundle_id,
        'resolved_surface_count': len(statbook_dict.get('rows') or {}),
        'contributor_row_count': len(response.contributor_rows),
        'trace_mode': trace_mode,
    }
    _annotate_display_fields(statbook_dict)
    return statbook_dict


_RUN_STATS_QUERY_OUTPUTS = {
    'start_of_run_rows': 'run_stats_query_rows_start_of_run.json',
    'max_progression_rows': 'run_stats_query_rows_max_progression.json',
    'start_of_run_plan': 'run_stats_query_plan_start_of_run.json',
    'max_progression_plan': 'run_stats_query_plan_max_progression.json',
}

def _remove_run_stats_legacy_outputs(out_dir: Path) -> None:
    _remove_legacy_outputs(out_dir, _RUN_STATS_LEGACY_OUTPUTS)


def _remove_run_stats_current_outputs(out_dir: Path) -> None:
    for filename in RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS:
        path = out_dir / filename
        if path.exists():
            try:
                path.unlink()
            except FileNotFoundError:
                continue
    perk_diag_dir = out_dir / 'diagnostics' / 'perks'
    if perk_diag_dir.exists():
        shutil.rmtree(perk_diag_dir, ignore_errors=True)


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


def _run_stats_progression_family_id(*, state_mode: str, perks_enabled: bool) -> str:
    if state_mode == 'start_of_run' and not perks_enabled:
        return 'progression_start_of_run'
    return 'progression_runtime_with_perks' if perks_enabled else 'progression_runtime_no_perks'


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
    if state_mode == 'start_of_run':
        return None, False
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


def _stable_run_stats_payload_for_commit(run_stats_payload: dict) -> dict:
    """Strip local timing telemetry from the committed run_stats baseline."""
    stable_payload = copy.deepcopy(run_stats_payload)
    diagnostics = dict(stable_payload.get('diagnostics') or {})
    diagnostics.pop('timings_ms', None)
    session = dict(diagnostics.get('session') or {})
    session.pop('account_state_build_ms', None)
    if session:
        diagnostics['session'] = session
    else:
        diagnostics.pop('session', None)
    preset_diagnostics = diagnostics.get('presets') or {}
    for preset_payload in preset_diagnostics.values():
        if not isinstance(preset_payload, dict):
            continue
        for state_mode in ('start_of_run', 'max_progression'):
            state_payload = dict(preset_payload.get(state_mode) or {})
            state_payload.pop('timings_ms', None)
            if state_payload:
                preset_payload[state_mode] = state_payload
    stable_payload['diagnostics'] = diagnostics
    return stable_payload


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
    entities = load_perk_entity_rows()
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
    entities = load_perk_entity_rows()
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
            json.dumps(_contract_json_payload(diag), indent=2),
            encoding='utf-8',
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


def _effective_manual_inputs_path(path: Path | None) -> Path:
    return path if path is not None else ROOT / 'input' / 'manual_inputs.yaml'


def _path_cache_token(path: Path) -> tuple[str, int | None, int | None]:
    resolved = path.resolve()
    try:
        stat = resolved.stat()
        return (str(resolved), stat.st_mtime_ns, stat.st_size)
    except OSError:
        return (str(resolved), None, None)


class RunStatsSession:
    """Warm in-process session for repeated bounded run_stats queries."""

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

    def get_account_state_bundle(
        self,
        *,
        ids_path: Path,
        manual_inputs_path: Path | None,
        perk_mode: str,
        diag_output_dir: Path | None,
    ):
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
                progression_family_id = _run_stats_progression_family_id(state_mode=state_mode, perks_enabled=perks_enabled)
                timing_family_id = _run_stats_timing_family_id(preset_name=preset_name, perks_enabled=perks_enabled)
                scenario_config = _run_stats_scenario_config(account_state, preset_name=preset_name)
                base_stat_inputs = tuple(compile_stat_inputs(
                    account_state,
                    preset_name=preset_name,
                    state_mode=state_mode,
                    perk_preset_name=perk_preset_name,
                    perks_enabled=perks_enabled,
                ))
                progression_bound = BoundStatInputs(
                    binding=bind_state_identity(
                        account_state,
                        preset_name=preset_name,
                        state_mode=state_mode,
                        perk_preset_name=perk_preset_name,
                        perks_enabled=perks_enabled,
                        scenario_context={'mode_id': 'progression'},
                    ),
                    stat_inputs=base_stat_inputs,
                )
                timing_bound = BoundStatInputs(
                    binding=bind_state_identity(
                        account_state,
                        state_mode=state_mode,
                        preset_name=preset_name,
                        perk_preset_name=perk_preset_name,
                        perks_enabled=perks_enabled,
                        scenario_context={
                            'mode_id': scenario_config.mode_id,
                            'tier': scenario_config.tier,
                            'league': scenario_config.league,
                            'tournament_wave': scenario_config.tournament_wave,
                        },
                    ),
                    stat_inputs=base_stat_inputs,
                )
                compiled_timing_family_rows = compile_timing_family_rows(
                    account_state=account_state,
                    family_id=timing_family_id,
                    preset_name=preset_name,
                    scenario_config=scenario_config,
                    perks_enabled=perks_enabled,
                    state_mode=state_mode,
                    perk_preset_name=perk_preset_name,
                    bound_stat_inputs=timing_bound,
                )

                t = perf_counter()
                progression_response = resolve_run_stats_progression_bundle(
                    account_state=account_state,
                    family_id=progression_family_id,
                    preset_name=preset_name,
                    perks_enabled=perks_enabled,
                    state_mode=state_mode,
                    perk_preset_name=perk_preset_name,
                    trace_mode='full_trace',
                    kernel=self.query_kernel if state_mode == 'start_of_run' else None,
                    bound_stat_inputs=progression_bound,
                    copy_result=False,
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
                    trace_mode='full_trace',
                    kernel=self.query_kernel if state_mode == 'start_of_run' else None,
                    compiled_family_rows=compiled_timing_family_rows,
                    copy_result=False,
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
                    trace_mode='full_trace',
                    kernel=self.query_kernel if state_mode == 'start_of_run' else None,
                    compiled_family_rows=compiled_timing_family_rows,
                    copy_result=False,
                )
                timing_wave_ms = _elapsed_ms(t)

                t = perf_counter()
                merged_statbook_dict = _merge_query_statbooks(
                    _query_response_to_statbook_dict(
                        progression_response,
                        bundle_id='progression_core_stats',
                        trace_mode='full_trace',
                        manual_advisory_inputs=input_bundle.manual_advisory_inputs,
                        account_state_labs=account_state.labs,
                        publish_qe_surfaces=True,
                    ),
                    _query_response_to_statbook_dict(
                        timing_core_response,
                        bundle_id='timing_core_cycle',
                        trace_mode='full_trace',
                        manual_advisory_inputs=input_bundle.manual_advisory_inputs,
                        account_state_labs=account_state.labs,
                    ),
                    _query_response_to_statbook_dict(
                        timing_wave_response,
                        bundle_id='timing_wave_duration',
                        trace_mode='full_trace',
                        manual_advisory_inputs=input_bundle.manual_advisory_inputs,
                        account_state_labs=account_state.labs,
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
        _remove_run_stats_current_outputs(args.out)
        _remove_run_stats_legacy_outputs(args.out)
        artifacts = self.build_run_stats_artifacts(args)
        diagnostics = artifacts['diagnostics']
        js = _json_sanitize
        write_start = perf_counter()
        (args.out / 'account_state.json').write_text(
            json.dumps(js(_sanitized_account_state_for_output(artifacts['account_state'], 'Farming')), indent=2, default=str)
        )
        (args.out / 'module_card_payloads.json').write_text(
            json.dumps(js(build_module_card_payloads(artifacts['account_state'])), indent=2, default=str)
        )
        input_dashboard_payload = _build_input_dashboard_payload(
            _sanitized_account_state_for_output(artifacts['account_state'], 'Farming'),
            diagnostics,
            qe_dashboard_publications={},
            module_card_payloads=build_module_card_payloads(artifacts['account_state']),
        )
        (args.out / 'input_dashboard.json').write_text(
            json.dumps(js(input_dashboard_payload), indent=2, default=str)
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['start_of_run_plan']).write_text(
            json.dumps(js({
                'pipeline_kind': 'run_stats_bounded_query',
                'state_mode': 'start_of_run',
                'presets': artifacts['state_query_plans']['start_of_run'],
            }), indent=2, default=str)
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['max_progression_plan']).write_text(
            json.dumps(js({
                'pipeline_kind': 'run_stats_bounded_query',
                'state_mode': 'max_progression',
                'presets': artifacts['state_query_plans']['max_progression'],
            }), indent=2, default=str)
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['start_of_run_rows']).write_text(
            json.dumps(js(artifacts['start_books_by_preset']), indent=2, default=str)
        )
        (args.out / _RUN_STATS_QUERY_OUTPUTS['max_progression_rows']).write_text(
            json.dumps(js(artifacts['max_books_by_preset']), indent=2, default=str)
        )
        stats_dashboard_payload = _build_stats_dashboard_payload(
            account_state_payload=_sanitized_account_state_for_output(artifacts['account_state'], 'Farming'),
            diagnostics=diagnostics,
            input_dashboard_payload=input_dashboard_payload,
            module_card_payloads=build_module_card_payloads(artifacts['account_state']),
            query_rows_start_of_run=artifacts['start_books_by_preset'],
            query_rows_max_progression=artifacts['max_books_by_preset'],
            ep_compare_publishable={},
            line_verification={},
            selected_preset='Farming',
            selected_state_mode='start_of_run',
        )
        (args.out / 'stats_dashboard.json').write_text(
            json.dumps(js(stats_dashboard_payload), indent=2, default=str)
        )
        diagnostics['output_contract'] = {
            'contract_kind': 'run_stats_bounded',
            'committed_baseline_artifacts': list(RUN_STATS_COMMITTED_BASELINE_ARTIFACTS),
            'local_support_artifacts': list(RUN_STATS_LOCAL_SUPPORT_ARTIFACTS),
            'all_local_output_artifacts': list(RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS),
            'product_artifact': 'run_stats.json',
            'query_row_artifacts': [_RUN_STATS_QUERY_OUTPUTS['start_of_run_rows'], _RUN_STATS_QUERY_OUTPUTS['max_progression_rows']],
            'query_plan_artifacts': [_RUN_STATS_QUERY_OUTPUTS['start_of_run_plan'], _RUN_STATS_QUERY_OUTPUTS['max_progression_plan']],
            'removed_legacy_fast_path_artifacts': list(_RUN_STATS_LEGACY_OUTPUTS),
            'ui_payload_artifacts': ['input_dashboard.json', 'module_card_payloads.json', 'stats_dashboard.json'],
        }
        stable_run_stats_payload = _stable_run_stats_payload_for_commit(artifacts['run_stats_payload'])
        (args.out / 'run_stats.json').write_text(json.dumps(js(stable_run_stats_payload), indent=2, default=str))
        diagnostics['timings_ms']['write_outputs_ms'] = _elapsed_ms(write_start)
        (args.out / 'diagnostics.json').write_text(json.dumps(js(diagnostics), indent=2, default=str))
        return 0


@lru_cache(maxsize=1)
def get_default_run_stats_session() -> RunStatsSession:
    return RunStatsSession()


def run_stats_pipeline(args) -> int:
    """
    Execute the fast stats pipeline.

    Wires: input -> qe -> out.
    Produces side-by-side start_of_run and max_progression composite stat views.
    Runs through the warm in-process run_stats session.
    """
    return get_default_run_stats_session().execute(args)


def run_analysis_pipeline(args) -> int:
    """
    Execute the full stat pipeline.

    Wires: input -> qe -> evaluators -> out.
    Transitional domain helpers sourced from run_stats module until T7.
    """
    args.state_mode = normalize_state_mode(args.state_mode)
    args.perk_state = _normalize_perk_state(args.perk_state)
    args.perk_mode = _normalize_perk_mode(getattr(args, 'perk_mode', None))
    args.out.mkdir(parents=True, exist_ok=True)

    from evaluators.compare import (
        COMPARE_DESTINATION_RUN_PERK_FACETS,
        COMPARE_PRESET_OVERRIDES,
        _apply_projected_runtime_compare_assumptions,
        _build_artifact_contract_manifest,
        _build_audit_surface_manifest,
        _build_compare_rows_by_preset,
        _build_compare_situation_fit_matrix,
        build_compare_status_summary as _build_compare_status_summary,
        _build_damage_defabs_scope_audit,
        build_ep_compare as _build_ep_compare,
        _build_family_completeness_matrix,
        _build_kb_gap_register,
        _build_kb_incomplete_areas,
        _build_kb_only_health_family_audit,
        build_line_by_line_verification as _build_line_by_line_verification,
        _build_perk_contributor_audit,
        _build_perk_coverage_audit,
        _build_publish_gate_audits,
        _build_publishable_statbook,
        _build_run_perk_residue_analysis,
        build_survivability_residue_analysis as _build_survivability_residue_analysis,
        build_survivor_closure_report as _build_survivor_closure_report,
        _build_tower_damage_residue_analysis,
        _build_tower_damage_runtime_gap_report,
        _build_tower_defense_absolute_semantic_gap_report,
        _build_tower_hp_semantic_gap_report,
        _build_tower_regen_closure_report,
        _build_tower_regen_ep_semantic_gap_report,
        _build_tradeoff_routing_audit,
        _compare_state_key_for_destination,
        _contributor_snapshot,
        _ep_stage_context_for_destination,
        _formula_contract,
        _is_calculator_scope_row,
        load_ep_oracle,
        load_formula_ledger,
        _normalize_compare_values,
        ensure_compare_authoritative_verdict_fields as _ensure_compare_authoritative_verdict_fields,
        ensure_line_verification_authoritative_verdict_fields as _ensure_line_verification_authoritative_verdict_fields,
    )
    from evaluators.compare_core import PreparedCompareRowsBundle
    from qe.query_routing import compiler_routing_indexes
    from input.state_types import PerkSelection
    from dataclasses import replace
    from evaluators.scorer import compute_optimizer_scores

    _manual_inputs_path = getattr(args, 'manual_inputs', None)
    _input_bundle = load_inputs(ids_path=args.ids, manual_inputs_path=_manual_inputs_path)
    ids_raw = _input_bundle.ids_raw
    loadout_config = _input_bundle.loadout_config
    perk_config, perk_config_resolution = _resolve_perk_config(
        perk_mode=args.perk_mode,
        primary_config=_input_bundle.perk_config,
        perk_policy=_input_bundle.perk_policy,
        ids_raw=ids_raw,
        diag_output_dir=args.out / 'diagnostics' / 'perks',
    )
    formula_ledger = load_formula_ledger()
    ep_oracle = load_ep_oracle()
    qe_planner = QEResolutionPlanner()

    def _prepare_compare_rows_bundle(state_mode: str, default_preset: str, perk_state: str) -> PreparedCompareRowsBundle:
        compare_rows_by_preset = {}
        compare_publishable_rows_by_preset = {}
        perk_state_by_preset = {}
        perk_materialized_by_preset = {}
        state_cache = {}

        def _state_for_preset(preset_name: str):
            state = state_cache.get(preset_name)
            if state is None:
                state = build_runtime_state(ids_raw, default_preset=preset_name, loadout_config=loadout_config, perk_config=perk_config)
                state_cache[preset_name] = state
            return state

        def _materialize(preset_name: str, forced_perk_state: str | None = None):
            state = _state_for_preset(preset_name)
            preset_perk_state = _normalize_perk_state(forced_perk_state) if forced_perk_state is not None else ('off' if preset_name == 'Tourney' else perk_state)
            perks_enabled_local = _perks_enabled_for_state(state.active_perk_preset, preset_perk_state)
            state_key = f'{preset_name}__perks_{preset_perk_state}' if forced_perk_state is not None else preset_name
            perk_state_by_preset[state_key] = preset_perk_state
            perk_materialized_by_preset[state_key] = perks_enabled_local
            snapshot = qe_planner.resolve_report_snapshot(
                state,
                preset_name=preset_name,
                state_mode=state_mode,
                perks_enabled=perks_enabled_local,
            )
            statbook = snapshot.statbook
            publish_query_surfaces(statbook.rows, account_state_labs=state.labs)
            statbook_dict_local = statbook.to_dict()
            for destination, row in statbook_dict_local.get('rows', {}).items():
                row['formula_contract'] = _formula_contract(formula_ledger, destination)
            publishable = _build_publishable_statbook(statbook_dict_local, formula_ledger)
            compare_rows_by_preset[state_key] = {str(k): v for k, v in statbook_dict_local.get('rows', {}).items()}
            compare_publishable_rows_by_preset[state_key] = {str(k): v for k, v in publishable.get('rows', {}).items()}
            return state

        default_state = _materialize(default_preset)
        _materialize('Tourney')
        _materialize('Tourney', forced_perk_state='on')
        _materialize('Farming', forced_perk_state='on')
        stage_context = {
            'state_mode': state_mode,
            'perk_state': perk_state,
            'perk_state_by_preset': dict(sorted(perk_state_by_preset.items())),
            'perk_materialized_by_preset': dict(sorted(perk_materialized_by_preset.items())),
            'active_perk_preset': _sanitized_active_perk_preset(default_state, default_preset),
            'default_compare_preset': default_preset,
            'active_cards_by_preset': {default_preset: list(default_state.card_presets.get(default_preset, []))},
            'active_modules_by_preset': {default_preset: {}},
            'modules_inventory': {},
        }
        return PreparedCompareRowsBundle(default_state, compare_rows_by_preset, compare_publishable_rows_by_preset, stage_context)

    prepared_bundle = _prepare_compare_rows_bundle(args.state_mode, args.preset, args.perk_state)
    (
        account_state,
        compare_rows_by_preset,
        compare_publishable_rows_by_preset,
        package_stage_context,
    ) = _build_compare_rows_by_preset(prepared_bundle)
    _annotate_compare_row_payloads_by_preset(compare_rows_by_preset)
    _annotate_compare_row_payloads_by_preset(compare_publishable_rows_by_preset)

    perks_enabled = _perks_enabled_for_state(account_state.active_perk_preset, args.perk_state)
    main_snapshot = qe_planner.resolve_report_snapshot(
        account_state,
        preset_name=args.preset,
        state_mode=args.state_mode,
        perks_enabled=perks_enabled,
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

    state_matrix = {}
    for state_mode in SUPPORTED_STATE_MODES:
        matrix_snapshot = qe_planner.resolve_report_snapshot(
            account_state,
            preset_name=args.preset,
            state_mode=state_mode,
            perks_enabled=perks_enabled,
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

    if args.state_mode == 'max_progression':
        projected_account_state = account_state
        projected_compare_rows_by_preset = compare_rows_by_preset
        projected_compare_publishable_rows_by_preset = compare_publishable_rows_by_preset
        projected_stage_context = package_stage_context
    else:
        projected_bundle = _prepare_compare_rows_bundle('max_progression', args.preset, args.perk_state)
        (
            projected_account_state,
            projected_compare_rows_by_preset,
            projected_compare_publishable_rows_by_preset,
            projected_stage_context,
        ) = _build_compare_rows_by_preset(projected_bundle)
        _annotate_compare_row_payloads_by_preset(projected_compare_rows_by_preset)
        _annotate_compare_row_payloads_by_preset(projected_compare_publishable_rows_by_preset)
    projected_ep_compare_publishable = _build_ep_compare(
        ep_oracle, projected_compare_publishable_rows_by_preset, formula_ledger,
        projected_stage_context, **_ep_kwargs
    )
    _annotate_compare_display_fields(projected_ep_compare_publishable)
    projected_compare_summary = _build_compare_status_summary(projected_ep_compare_publishable)

    run_stats_artifacts = get_default_run_stats_session().build_run_stats_artifacts(args)

    def _query_rows_payload(books_by_preset: dict[str, dict], *, state_mode: str) -> dict[str, dict[str, object]]:
        payload: dict[str, dict[str, object]] = {}
        for preset_name, statbook_payload in (books_by_preset or {}).items():
            payload[str(preset_name)] = {
                'rows': {str(surface_id): dict(row or {}) for surface_id, row in dict((statbook_payload or {}).get('rows') or {}).items()},
                'diagnostics': {
                    'pipeline_kind': 'run_stats_bounded_query',
                    'state_mode': state_mode,
                    'family_ids': list(((statbook_payload or {}).get('diagnostics') or {}).get('family_ids') or []),
                    'bundle_ids': list(((statbook_payload or {}).get('diagnostics') or {}).get('bundle_ids') or []),
                },
            }
        return payload

    dashboard_query_rows_start_payload = _query_rows_payload(
        run_stats_artifacts.get('start_books_by_preset') or {},
        state_mode='start_of_run',
    )
    dashboard_query_rows_max_payload = _query_rows_payload(
        run_stats_artifacts.get('max_books_by_preset') or {},
        state_mode='max_progression',
    )

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
    perk_entities = load_perk_entities()
    perk_effects = load_perk_effects()
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
    all_perk_rows = [row for row in compile_stat_inputs(audit_state, preset_name=account_state.default_preset, state_mode='start_of_run') if row.source_family == 'perk']
    contributor_stat_inputs_by_preset = {
        preset_name: compile_stat_inputs(account_state, preset_name=preset_name, state_mode=args.state_mode, perks_enabled=True)
        for preset_name in ("Farming", "Tourney")
    }

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
        'qe_resolution_interface': statbook.diagnostics.get('qe_resolution_interface'),
        'qe_resolution_backend': statbook.diagnostics.get('qe_resolution_backend'),
        'qe_native_family_available': statbook.diagnostics.get('qe_native_family_available'),
        'qe_native_family_id': statbook.diagnostics.get('qe_native_family_id'),
        'qe_native_family_merge': statbook.diagnostics.get('qe_native_family_merge'),
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
            perk_entities,
            perk_effects,
            PERK_TARGET_DESTINATION_OVERRIDES,
            all_perk_rows,
            canon_stats,
            alias_index,
            None,
        ),
        'tower_damage_residue_analysis': _build_tower_damage_residue_analysis(
            projected_ep_compare_publishable if args.state_mode != 'max_progression' else ep_compare_publishable
        ),
        'run_perk_residue_analysis': _build_run_perk_residue_analysis(
            projected_ep_compare_publishable if args.state_mode != 'max_progression' else ep_compare_publishable
        ),
        'tradeoff_routing_audit': _build_tradeoff_routing_audit(
            compile_stat_inputs(account_state, preset_name=args.preset, state_mode=args.state_mode, perks_enabled=perks_enabled),
            perk_entities,
            TRADE_OFF_BENEFIT_EFFECT_INDEXES,
            {str(item).strip() for item in (perk_config or {}).get('banned_perk_ids', []) if str(item).strip()},
            preset=args.preset, state_mode=args.state_mode, perk_state=args.perk_state,
        ),
        'perk_contributor_audit': _build_perk_contributor_audit(
            contributor_stat_inputs_by_preset
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
        compare_states = {
            'current': {'preset': args.preset, 'perk_state': args.perk_state, 'compare': ep_compare_publishable},
            'projected': {'preset': args.preset, 'perk_state': args.perk_state, 'compare': projected_ep_compare_publishable},
        }
        diagnostics['compare_situation_fit_matrix'] = _build_compare_situation_fit_matrix(compare_states)
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

    # Prepare payloads and delegate output writing to publication authority
    account_state_payload = _sanitized_account_state_for_output(account_state, args.preset)
    stat_inputs_payload = [row.to_dict() for row in stat_inputs]
    module_card_payloads_data = build_module_card_payloads(account_state)
    qe_dashboard_publications = _build_input_dashboard_qe_publications(
        account_state=account_state,
        compare_rows_by_preset=compare_rows_by_preset,
        projected_compare_rows_by_preset=projected_compare_rows_by_preset,
        stat_inputs=stat_inputs,
        preset_name=args.preset,
    )

    write_core_outputs(
        out_dir=args.out,
        diagnostics=diagnostics,
        account_state_payload=account_state_payload,
        stat_inputs_payload=stat_inputs_payload,
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
        root_path=ROOT,
        module_card_payloads=module_card_payloads_data,
        qe_dashboard_publications=qe_dashboard_publications,
        query_rows_start_of_run=dashboard_query_rows_start_payload,
        query_rows_max_progression=dashboard_query_rows_max_payload,
        selected_preset=args.preset,
        selected_state_mode=args.state_mode,
    )

    # Write module card payloads (QE-generated orchestration artifact, PR329)
    (args.out / 'module_card_payloads.json').write_text(
        json.dumps(_contract_json_payload(module_card_payloads_data), indent=2, default=str)
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
            try:
                stale_path.unlink()
            except FileNotFoundError:
                continue

    return 0


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
            outputs_summary={
                'ids_path': _relpath_str(request.ids),
                'manual_inputs_path': _relpath_str(_effective_manual_inputs_path(request.manual_inputs)),
                'section_names': diagnostics.get('section_names', []),
                'section_row_counts': diagnostics.get('section_row_counts', {}),
            },
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
                'line_verification_summary': diagnostics.get('line_verification_summary', {}),
                'state_matrix_modes': list((diagnostics.get('state_matrix') or {}).keys()),
            },
        ),
        PipelineStageRecord(
            stage_id='artifact_write',
            title='Artifact write',
            owner_module='app.publication',
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
    args = type('PipelineArgs', (), {})()
    args.ids = request.ids
    args.out = request.out
    args.preset = request.preset
    args.state_mode = request.state_mode
    args.manual_inputs = request.manual_inputs
    args.perk_mode = request.perk_mode
    args.include_slow_audits = request.include_slow_audits
    args.perk_state = request.perk_state
    exit_code = run_analysis_pipeline(args)
    diagnostics = _load_json_artifact(request.out / 'diagnostics.json')
    total_elapsed_ms = round((perf_counter() - started_at) * 1000.0, 3)
    pipeline_trace = _build_pipeline_trace_from_artifacts(
        request=request,
        total_elapsed_ms=total_elapsed_ms,
        diagnostics=diagnostics,
    )
    generated_files = _generated_output_paths(request.out)
    pipeline_trace = PipelineTrace(
        request=pipeline_trace.request,
        execution_path=pipeline_trace.execution_path,
        stages=pipeline_trace.stages,
        artifacts_written=[_relpath_str(path) for path in generated_files],
    )
    write_pipeline_trace(request.out, pipeline_trace, ROOT)
    generated_files = _generated_output_paths(request.out)
    return PipelineRunResult(
        exit_code=int(exit_code),
        request=request,
        out_dir=request.out,
        diagnostics=diagnostics,
        generated_files=tuple(generated_files),
        pipeline_trace=pipeline_trace,
    )


def build_verification_snapshot_set(
    base_request: PipelineRunRequest,
    specs: tuple[VerificationSnapshotSpec, ...] | list[VerificationSnapshotSpec] | None = None,
) -> list[PipelineRunResult]:
    requests = _default_verification_matrix_requests(base_request) if specs is None else tuple(
        PipelineRunRequest(
            ids=base_request.ids,
            out=base_request.out / (spec.out_subdir or f'{spec.preset.lower()}_{spec.state_mode}'),
            preset=spec.preset,
            state_mode=spec.state_mode,
            manual_inputs=base_request.manual_inputs,
            perk_mode=base_request.perk_mode,
            include_slow_audits=base_request.include_slow_audits,
            perk_state=spec.perk_state,
        )
        for spec in specs
    )
    results: list[PipelineRunResult] = []
    for request in requests:
        results.append(execute_pipeline(request))
    return results


def _default_verification_matrix_requests(base_request: PipelineRunRequest) -> tuple[PipelineRunRequest, ...]:
    specs = (
        VerificationSnapshotSpec('Farming', 'start_of_run'),
        VerificationSnapshotSpec('Farming', 'max_progression'),
        VerificationSnapshotSpec('Tourney', 'start_of_run', perk_state='off'),
        VerificationSnapshotSpec('Tourney', 'max_progression', perk_state='off'),
    )
    return tuple(
        PipelineRunRequest(
            ids=base_request.ids,
            out=base_request.out / (spec.out_subdir or f'{spec.preset.lower()}_{spec.state_mode}'),
            preset=spec.preset,
            state_mode=spec.state_mode,
            manual_inputs=base_request.manual_inputs,
            perk_mode=base_request.perk_mode,
            include_slow_audits=base_request.include_slow_audits,
            perk_state=spec.perk_state,
        )
        for spec in specs
    )


def resolve_fast_checkpoint(request: FastCheckpointRequest) -> FastCheckpointResult:
    if not request.requested_surface_ids:
        raise ValueError('requested_surface_ids must not be empty: fast checkpoint resolution requires at least one surface id.')

    input_bundle, account_state, _perk_config_resolution = _build_account_state(
        ids_path=request.ids,
        manual_inputs_path=request.manual_inputs,
        preset=request.preset,
        perk_mode=request.perk_mode,
        diag_output_dir=None,
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
        trace_mode='full_trace',
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
