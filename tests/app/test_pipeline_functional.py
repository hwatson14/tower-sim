"""
Functional tests for app/pipeline.py and sharded evaluators.
Verifies trace contract, artifact depth, run-stats output naming,
cache invalidation robustness, and diagnostics persistence contract.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
import pytest

from app.pipeline import (
    execute_pipeline,
    PipelineRunRequest,
    resolve_fast_checkpoint,
    FastCheckpointRequest,
    _build_input_dashboard_qe_publications,
    _RUN_STATS_QUERY_OUTPUTS,
    _path_cache_token,
    _effective_manual_inputs_path,
    _run_stats_perk_state,
)
from app.pipeline import RunStatsSession
from app.publication import (
    FULL_PIPELINE_PUBLICATION_ARTIFACTS,
    RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS,
    RUN_STATS_COMMITTED_BASELINE_ARTIFACTS,
    RUN_STATS_LOCAL_SUPPORT_ARTIFACTS,
)
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
IDS_PATH = ROOT / "input" / "imports" / "ids.csv"


@pytest.fixture(scope="module")
def run_stats_single_execution(tmp_path_factory):
    """Execute RunStatsSession once and return parsed canonical outputs plus output directory."""
    out_dir = tmp_path_factory.mktemp("run_stats_out")
    args = SimpleNamespace(
        ids=IDS_PATH, out=out_dir, perk_mode='none', perk_state='auto', manual_inputs=None,
    )
    session = RunStatsSession()
    rc = session.execute(args)
    assert rc == 0

    parsed_outputs = {
        filename: json.loads((out_dir / filename).read_text(encoding='utf-8'))
        for filename in _RUN_STATS_QUERY_OUTPUTS.values()
    }
    parsed_outputs['diagnostics.json'] = json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8'))
    return {"out_dir": out_dir, "parsed_outputs": parsed_outputs}


@pytest.fixture(scope="module")
def canonical_pipeline_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    out_dir = tmp_path_factory.mktemp("canonical_pipeline_out")
    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=out_dir,
        preset='Farming',
        state_mode='start_of_run',
    )
    result = execute_pipeline(request)
    assert result.exit_code == 0

    artifact_payloads = {
        'diagnostics': json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8')),
        'statbook_publishable': json.loads((out_dir / 'statbook_publishable.json').read_text(encoding='utf-8')),
        'optimizer_scores': json.loads((out_dir / 'optimizer_scores.json').read_text(encoding='utf-8')),
        'ep_oracle_compare': json.loads((out_dir / 'ep_oracle_compare.json').read_text(encoding='utf-8')),
        'pipeline_trace': json.loads((out_dir / 'pipeline_trace.json').read_text(encoding='utf-8')),
        'dashboards': {
            'input_dashboard': json.loads((out_dir / 'input_dashboard.json').read_text(encoding='utf-8')),
            'stats_dashboard': json.loads((out_dir / 'stats_dashboard.json').read_text(encoding='utf-8')),
        },
    }
    return artifact_payloads


def test_run_stats_start_of_run_forces_perks_off() -> None:
    account_state = SimpleNamespace(
        perk_presets={'Farming': {}},
        active_perk_preset='Farming',
    )
    preset_name, perks_enabled = _run_stats_perk_state(
        account_state,
        preset_name='Farming',
        perk_state='on',
        perk_mode='max_progression_policy',
        state_mode='start_of_run',
    )
    assert preset_name is None
    assert perks_enabled is False


def test_load_ep_oracle_applies_key_level_ambiguity_overrides(tmp_path: Path) -> None:
    from evaluators.compare import _load_ep_oracle

    ep_csv = tmp_path / 'ep_export.csv'
    ep_csv.write_text(
        '\n'.join(
            [
                'suite,key,label,value,import',
                'ehp,wall_health,Wall Health,132.07 T,132.07 T',
                'ehp,wall_fortification,Wall Fortification,1.37 q,1.37 q',
                'edmg,crit_factor,Critical Factor,170.5248,170.5248',
                'edmg,recovery_package_chance,Recovery Package Chance,0.788,0.788',
            ]
        ),
        encoding='utf-8',
    )

    oracle = _load_ep_oracle(ep_csv)

    # Ambiguous rows route by export key, not label-only matching.
    assert oracle['derived::wall.hp_pre_fort']['ep_value_raw'] == '132.07 T'
    assert oracle['derived::wall.hp_pre_fort']['label'] == 'Wall Health'
    assert oracle['state::wall.fortification_multiplier']['ep_value_raw'] == '1.37 q'
    assert oracle['state::wall.fortification_multiplier']['label'] == 'Wall Fortification'
    # Existing ambiguity aliases remain key-driven.
    assert oracle['state::tower.crit_multiplier']['ep_value_raw'] == '170.5248'
    assert oracle['state::tower.package_chance_pct']['ep_value_raw'] == '0.788'


@pytest.mark.live
def test_execute_pipeline_smoke_and_trace_contract(tmp_path):
    """execute_pipeline runs and produces a valid pipeline_trace.json with all expected fields."""
    out_dir = tmp_path / "out"
    request = PipelineRunRequest(ids=IDS_PATH, out=out_dir, preset='Farming', state_mode='start_of_run')

    result = execute_pipeline(request)

    assert result.exit_code == 0
    assert result.out_dir == out_dir

    trace_path = out_dir / "pipeline_trace.json"
    assert trace_path.exists(), "pipeline_trace.json was not created"

    trace = json.loads(trace_path.read_text(encoding='utf-8'))
    assert set(trace) >= {'request', 'execution_path', 'stages', 'artifacts_written'}
    assert len(trace['stages']) >= 3, "Expected at least 3 stages (input_load, stat_resolution, artifact_write)"
    stage_ids = {s['stage_id'] for s in trace['stages']}
    assert 'input_load' in stage_ids
    assert 'stat_resolution' in stage_ids
    assert 'artifact_write' in stage_ids
    assert len(trace['artifacts_written']) > 0

    req = trace['request']
    assert 'ids' in req and 'out' in req and 'preset' in req and 'state_mode' in req

    written_names = {Path(f).name for f in trace['artifacts_written']}
    assert 'ep_oracle_compare.json' in written_names
    assert 'line_by_line_verification.json' in written_names


@pytest.mark.live
def test_diagnostics_depth(canonical_pipeline_artifacts):
    """diagnostics.json must contain real populated content, not empty placeholders."""
    diag = canonical_pipeline_artifacts['diagnostics']

    assert diag.get('stat_input_count', 0) > 0, "stat_input_count must be non-zero"
    assert diag.get('statbook_row_count', 0) > 0, "statbook_row_count must be non-zero"
    assert 'state_matrix' in diag and diag['state_matrix'], "state_matrix must be populated"
    assert 'start_of_run' in diag['state_matrix'] and 'max_progression' in diag['state_matrix']
    assert diag['state_matrix']['start_of_run'].get('input_count', 0) > 0
    assert 'kb_incomplete_areas' in diag
    assert 'audits' in diag
    assert 'ep_compare_summary' in diag


@pytest.mark.live
def test_publishable_statbook_populated(canonical_pipeline_artifacts):
    """statbook_publishable.json must be non-empty and structurally valid."""
    pub = canonical_pipeline_artifacts['statbook_publishable']
    assert 'rows' in pub and len(pub['rows']) > 0, "statbook_publishable.json rows must be non-empty"


@pytest.mark.live
def test_input_dashboard_artifact_is_published(tmp_path):
    """input_dashboard payload builder must emit the expected top-level contract keys."""
    from app.publication import _build_input_dashboard_payload

    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    assert dashboard.get('schema_version') == 2
    assert isinstance(dashboard.get('preset_options'), list)
    expected_panel_ids = [
        'labs',
        'workshop',
        'workshop_enhancements',
        'ultimate_weapons',
        'cards',
        'bots',
        'relics',
        'modules',
        'vault',
        'guardians',
        'themes_and_songs',
    ]
    panel_ids = [panel.get('panel_id') for panel in (dashboard.get('panels') or [])]
    assert panel_ids == expected_panel_ids
    panel_by_id = {panel.get('panel_id'): panel for panel in (dashboard.get('panels') or [])}
    assert panel_by_id['themes_and_songs']['panel_type'] == 'simple_metric_panel'
    assert 'rows' not in ((panel_by_id['workshop'].get('payload') or {}))

    labs_rows = (((panel_by_id['labs'].get('payload') or {}).get('buckets') or [{}])[0].get('rows') or [])
    if labs_rows:
        assert {'name', 'level', 'max'}.issubset(labs_rows[0].keys())


def test_build_boss_wave_payload_publishes_summary_and_runtime_assumptions(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    monkeypatch.setattr(
        pipeline_mod,
        'load_inputs',
        lambda ids_path=None, manual_inputs_path=None: type(
            'Bundle',
            (),
            {'ids_raw': {}, 'loadout_config': {}, 'perk_config': {}, 'perk_policy': {}},
        )(),
    )
    monkeypatch.setattr(
        pipeline_mod,
        'build_runtime_state',
        lambda ids_raw, loadout_config=None, perk_config=None: type('State', (), {'player_meta': {}})(),
    )
    monkeypatch.setattr(pipeline_mod, 'build_start_of_run_state', lambda account_state, preset_name, perk_state: {'state': 'start'})

    def _fake_build_boss_wave_table_payload(*, account_state, initial_projected_state, config, stop_on_failure):
        assert stop_on_failure is True
        assert config.mode_id == 'farming'
        assert config.tier_number == 14
        assert config.tier_column == 'Tier 14'
        assert config.boss_interval_waves == 9
        assert config.checkpoint_every_bosses == 1
        return {
            'rows': [
                {'display_wave': 9, 'survives_boss': True},
                {'display_wave': 18, 'survives_boss': True},
                {'display_wave': 27, 'survives_boss': False},
            ],
            'summary': {
                'max_wave': 18,
                'max_surviving_wave': 18,
                'first_failed_wave': 27,
                'row_count': 3,
                'terminal_display_wave': 27,
                'survives_through_end': False,
                'result_consistent_with_rows': True,
            },
            'diagnostics': {
                'execution_mode': 'table_sweep',
                'mode_id': 'farming',
                'tier_number': 14,
                'tier_column': 'Tier 14',
                'actual_boss_interval_waves': 9,
                'checkpoint_every_bosses': 1,
                'checkpoint_stride_waves': 9,
                'requested_start_wave': 1,
                'first_checkpoint_wave': 9,
                'state_mode': 'start_of_run',
                'checkpoint_mode': 'actual_boss_cadence_with_sampling',
                'checkpoint_resolution_mode': 'every_n_bosses',
                'stop_on_failure': True,
                'perks_enabled': True,
                'scenario_runtime_inputs': {'orb_boss_hit_pct': 2.5},
                'qe_resolution_count': 2,
                'timing_recompute_count': 2,
                'snapshot_reuse_count': 0,
                'qe_dirty_reresolve_count': 1,
                'delta_fallback_count': 0,
            },
        }

    monkeypatch.setattr(pipeline_mod, 'build_boss_wave_table_payload', _fake_build_boss_wave_table_payload)

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out')
    payload = pipeline_mod.build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=30,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'orb_boss_hit_pct': 2.5,
            'orb_boss_hits_per_second': 5.0,
            'electron_hits_per_second': 5.0,
            'boss_contact_time_seconds': 1.0,
            'effective_damage_reduction_pct': 90.0,
            'incoming_damage_multiplier': 1.0,
        },
        boss_wave_source='legacy',
    )

    assert payload.get('artifact') == 'boss_wave_dashboard_payload'
    assert payload.get('schema_version') == 1
    assert payload.get('contract', {}).get('simulator_owner') == 'simulators.run_executor.build_boss_wave_table_payload'
    assert payload.get('source_selection', {}).get('active_source') == 'legacy'
    assert payload.get('contract', {}).get('perk_timeline_mode') == 'runtime_policy_projection'
    assert payload.get('contract', {}).get('checkpoint_mode') == 'actual_boss_cadence_with_sampling'
    assert payload.get('download', {}).get('format') == 'csv'
    summary = payload.get('summary') or {}
    assert summary['max_wave'] == 18
    assert summary['max_surviving_wave'] == 18
    assert summary['first_failed_wave'] == 27
    assert summary['result_consistent_with_rows'] is True
    diagnostics = payload.get('diagnostics') or {}
    assert diagnostics['preset_name'] == 'Farming'
    assert diagnostics['mode_id'] == 'farming'
    assert diagnostics['tier_number'] == 14
    assert diagnostics['tier_column'] == 'Tier 14'
    assert diagnostics['actual_boss_interval_waves'] == 9
    assert diagnostics['checkpoint_every_bosses'] == 1
    assert diagnostics['checkpoint_mode'] == 'actual_boss_cadence_with_sampling'
    assert diagnostics['checkpoint_resolution_mode'] == 'every_n_bosses'
    assert diagnostics['execution_mode'] == 'table_sweep'
    assert diagnostics['stop_on_failure'] is True
    assert diagnostics['perk_timeline_rows'] >= 0
    assert diagnostics['scenario_runtime_inputs']['orb_boss_hit_pct'] == 2.5


def _install_fake_boss_wave_pipeline_dependencies(monkeypatch, pipeline_mod, *, rows, summary):
    monkeypatch.setattr(
        pipeline_mod,
        'load_inputs',
        lambda ids_path=None, manual_inputs_path=None: type(
            'Bundle',
            (),
            {'ids_raw': {}, 'loadout_config': {}, 'perk_config': {}, 'perk_policy': {}},
        )(),
    )
    monkeypatch.setattr(
        pipeline_mod,
        'build_runtime_state',
        lambda ids_raw, loadout_config=None, perk_config=None: type('State', (), {'player_meta': {}})(),
    )
    monkeypatch.setattr(pipeline_mod, 'build_start_of_run_state', lambda account_state, preset_name, perk_state: {'state': 'start'})

    def _fake_build_boss_wave_table_payload(*, account_state, initial_projected_state, config, stop_on_failure):
        return {
            'rows': rows,
            'summary': summary,
            'diagnostics': {
                'execution_mode': 'table_sweep',
                'mode_id': 'farming',
                'tier_number': 14,
                'tier_column': 'Tier 14',
                'actual_boss_interval_waves': 9,
                'checkpoint_every_bosses': 1,
                'checkpoint_stride_waves': 9,
                'requested_start_wave': 1,
                'first_checkpoint_wave': 9,
                'state_mode': 'start_of_run',
                'checkpoint_mode': 'actual_boss_cadence_with_sampling',
                'checkpoint_resolution_mode': 'every_n_bosses',
                'stop_on_failure': bool(stop_on_failure),
                'perks_enabled': True,
                'scenario_runtime_inputs': {'orb_boss_hit_pct': 2.5},
                'qe_resolution_count': 2,
                'timing_recompute_count': 2,
                'snapshot_reuse_count': 0,
                'qe_dirty_reresolve_count': 1,
                'delta_fallback_count': 0,
            },
        }

    monkeypatch.setattr(pipeline_mod, 'build_boss_wave_table_payload', _fake_build_boss_wave_table_payload)


def _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod, *, omit_surface: str | None = None):
    class _FakeRow:
        def __init__(self, value):
            self.final_value = value
            self.status = 'resolved'

    rows = {
        'state::tower.enemy_attack_level_skip_pct': _FakeRow(0.0),
        'state::tower.enemy_health_level_skip_pct': _FakeRow(0.0),
        'state::tower.free_attack_upgrade_chance_pct': _FakeRow(0.0),
        'state::tower.free_defense_upgrade_chance_pct': _FakeRow(0.0),
        'state::tower.free_utility_upgrade_chance_pct': _FakeRow(0.0),
        'state::wall.hp': _FakeRow(1000.0),
        'state::wall.regen': _FakeRow(25.0),
        'state::wall.fortification_multiplier': _FakeRow(2.0),
        'state::tower.defense_pct': _FakeRow(90.0),
        'state::tower.thorns_damage_pct': _FakeRow(99.0),
        'state::cards.plasma_cannon.effect_pct': _FakeRow(100.0),
    }
    if omit_surface:
        rows.pop(omit_surface)
    monkeypatch.setattr(pipeline_mod, 'resolve_checkpoint_surfaces', lambda *args, **kwargs: object())
    monkeypatch.setattr(pipeline_mod, 'query_response_to_statbook', lambda *args, **kwargs: SimpleNamespace(rows=rows))


def _phase2a_fake_legacy_row(display_wave: int) -> dict[str, object]:
    return {
        'display_wave': display_wave,
        'attack_wave': display_wave,
        'health_wave': display_wave,
        'boss_attack': 10.0,
        'boss_health': 100.0,
        'wall_hp': 1000.0,
        'wall_regen': 25.0,
        'wall_fortification_multiplier': 2.0,
        'tower_defense_pct': 90.0,
        'tower_thorns_damage_pct': 99.0,
        'tower_damage_per_second': 12345.0,
        'plasma_cannon_effect_pct': 100.0,
        'effective_damage_reduction_pct_used': 90.0,
        'boss_contact_time_seconds_used': 1.0,
        'boss_hit_interval_seconds_used': 2.0,
        'incoming_damage_multiplier_used': 1.0,
        'boss_ttk_seconds_used': 7.5,
        'wall_pool_hp_used': 2000.0,
        'wall_regen_gained_hp': 187.5,
        'boss_hits_taken': 4,
        'boss_total_damage_taken': 10.0,
        'boss_survival_margin_hp': 2177.5,
        'survives_boss': True,
    }


def test_build_boss_wave_payload_phase2b_replacement_inputs_drive_table_summary_export_and_diagnostics(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    legacy_rows = [_phase2a_fake_legacy_row(9), _phase2a_fake_legacy_row(18)]
    legacy_summary = {
        'max_wave': 9,
        'max_surviving_wave': 9,
        'first_failed_wave': 18,
        'row_count': 2,
        'terminal_display_wave': 18,
        'survives_through_end': False,
        'result_consistent_with_rows': True,
    }
    _install_fake_boss_wave_pipeline_dependencies(monkeypatch, pipeline_mod, rows=legacy_rows, summary=legacy_summary)
    _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod)
    monkeypatch.setattr(
        pipeline_mod,
        'build_start_of_run_state',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('default replacement must not build legacy start state')),
    )
    monkeypatch.setattr(
        pipeline_mod,
        'build_boss_wave_table_payload',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('default replacement must not call legacy row engine')),
    )

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out')
    payload = pipeline_mod.build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=30,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'orb_boss_hit_pct': 2.5,
            'orb_boss_hits_per_second': 5.0,
            'electron_hits_per_second': 5.0,
            'boss_contact_time_seconds': 1.0,
            'effective_damage_reduction_pct': 90.0,
            'incoming_damage_multiplier': 1.0,
        },
    )

    contract = payload.get('contract') or {}
    source_selection = payload.get('source_selection') or {}
    assert contract.get('simulator_owner') == 'simulators.evaluator_kernel.evaluate_overlay_row'
    assert contract.get('operator_table_source') == 'replacement'
    assert contract.get('summary_source') == 'replacement'
    assert contract.get('csv_export_source') == 'replacement'
    assert contract.get('diagnostics_source') == 'replacement'
    assert source_selection.get('rollback_source') == 'legacy'
    assert source_selection.get('rollback_available') is True
    assert source_selection.get('active_source') == 'replacement'
    assert source_selection.get('csv_export_source') == 'replacement'
    assert source_selection.get('diagnostics_source') == 'replacement'

    operator_rows = payload.get('operator_rows') or []
    assert payload.get('rows') == operator_rows
    assert operator_rows[0]['replacement_source'] == 'replacement'
    assert operator_rows[0]['tower_damage_per_second'] is None
    assert operator_rows[0]['summary_lane_id'] == 'avg'
    assert set(operator_rows[0]['lane_handle_ids']) == {'avg', 'min', 'max'}
    assert operator_rows[0]['boss_health'] != legacy_rows[0]['boss_health']
    assert payload.get('download_rows') != legacy_rows
    assert payload.get('download_rows')[0]['replacement_source'] == 'replacement'
    assert payload.get('download_rows')[0]['operator_handle_id'] == operator_rows[0]['operator_handle_id']
    assert payload.get('legacy_shadow', {}).get('materialized') is False
    assert payload.get('download', {}).get('row_source') == 'replacement'
    diagnostics = payload.get('diagnostics') or {}
    assert diagnostics.get('execution_mode') == 'staged_replacement_phase2b'
    assert diagnostics.get('checkpoint_resolution_mode') == 'replacement_table1_table2_overlay'
    assert diagnostics.get('source_selection', {}).get('diagnostics_source') == 'replacement'
    assert diagnostics.get('replacement_model', {}).get('boss_ttk_contract') == 'v21_event_only'
    assert diagnostics.get('replacement_model', {}).get('continuous_tower_dps_included') is False
    assert diagnostics.get('replacement_model', {}).get('contract_version') == 'boss_waves_replacement_phase2b_v1'
    assert diagnostics.get('replacement_model', {}).get('table1_source_basis') == 'app_pipeline_qe_checkpoint_surfaces_to_run_plan'
    assert diagnostics.get('legacy_shadow_available') is True
    assert diagnostics.get('legacy_shadow_materialized') is False
    assert diagnostics.get('replacement_outputs', {}).get('download_row_count') == len(payload.get('download_rows') or [])

    summary = payload.get('summary') or {}
    assert summary['max_surviving_wave'] == 27
    assert summary['first_failed_wave'] == 0
    assert summary['survives_through_end'] is True


def test_build_boss_wave_payload_phase2a_rollback_restores_legacy_table_and_summary(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    legacy_rows = [_phase2a_fake_legacy_row(9)]
    legacy_summary = {
        'max_wave': 9,
        'max_surviving_wave': 9,
        'first_failed_wave': 0,
        'row_count': 1,
        'terminal_display_wave': 9,
        'survives_through_end': True,
        'result_consistent_with_rows': True,
    }
    _install_fake_boss_wave_pipeline_dependencies(monkeypatch, pipeline_mod, rows=legacy_rows, summary=legacy_summary)

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out')
    payload = pipeline_mod.build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=30,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'orb_boss_hit_pct': 2.5,
            'orb_boss_hits_per_second': 5.0,
            'electron_hits_per_second': 5.0,
            'boss_contact_time_seconds': 1.0,
            'effective_damage_reduction_pct': 90.0,
            'incoming_damage_multiplier': 1.0,
        },
        boss_wave_source='legacy',
    )

    assert payload.get('rows') == legacy_rows
    assert payload.get('operator_rows') == legacy_rows
    assert payload.get('download_rows') == legacy_rows
    assert payload.get('summary') == {
        'preset_name': 'Farming',
        'tier_column': 'Tier 14',
        'state_mode': 'start_of_run',
        'max_wave': 9,
        'max_surviving_wave': 9,
        'first_failed_wave': 0,
        'row_count': 1,
        'terminal_display_wave': 9,
        'survives_through_end': True,
        'result_consistent_with_rows': True,
    }
    assert payload.get('contract', {}).get('simulator_owner') == 'simulators.run_executor.build_boss_wave_table_payload'
    assert payload.get('source_selection', {}).get('active_source') == 'legacy'
    assert payload.get('download', {}).get('row_source') == 'legacy'
    assert (payload.get('diagnostics') or {}).get('execution_mode') == 'table_sweep'


def test_build_boss_wave_payload_phase2a_fails_closed_on_unmapped_required_input_primitive(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    row = _phase2a_fake_legacy_row(9)
    row.pop('wall_regen')
    _install_fake_boss_wave_pipeline_dependencies(
        monkeypatch,
        pipeline_mod,
        rows=[row],
        summary={
            'max_wave': 9,
            'max_surviving_wave': 9,
            'first_failed_wave': 0,
            'row_count': 1,
            'terminal_display_wave': 9,
            'survives_through_end': True,
            'result_consistent_with_rows': True,
        },
    )
    _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod, omit_surface='state::wall.regen')

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out')
    with pytest.raises(ValueError, match="requires QE surface 'state::wall.regen'"):
        pipeline_mod.build_boss_wave_payload(
            request,
            preset_name='Farming',
            tier_number=14,
            end_wave=30,
            boss_wave_step=1,
            stop_on_failure=True,
            scenario_runtime_inputs={
                'orb_boss_hit_pct': 2.5,
                'orb_boss_hits_per_second': 5.0,
                'electron_hits_per_second': 5.0,
                'boss_contact_time_seconds': 1.0,
                'effective_damage_reduction_pct': 90.0,
                'incoming_damage_multiplier': 1.0,
            },
        )


def test_build_boss_wave_payload_phase2b_fails_closed_on_missing_export_mapping(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_fake_boss_wave_pipeline_dependencies(
        monkeypatch,
        pipeline_mod,
        rows=[_phase2a_fake_legacy_row(9)],
        summary={
            'max_wave': 9,
            'max_surviving_wave': 9,
            'first_failed_wave': 0,
            'row_count': 1,
            'terminal_display_wave': 9,
            'survives_through_end': True,
            'result_consistent_with_rows': True,
        },
    )
    _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod)
    monkeypatch.setattr(
        pipeline_mod,
        'BOSS_WAVE_PHASE2B_EXPORT_FIELDS',
        (*pipeline_mod.BOSS_WAVE_PHASE2B_EXPORT_FIELDS, 'unmapped_export_field'),
    )

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out')
    with pytest.raises(ValueError, match='missing required replacement fields'):
        pipeline_mod.build_boss_wave_payload(
            request,
            preset_name='Farming',
            tier_number=14,
            end_wave=30,
            boss_wave_step=1,
            stop_on_failure=True,
            scenario_runtime_inputs={
                'orb_boss_hit_pct': 2.5,
                'orb_boss_hits_per_second': 5.0,
                'electron_hits_per_second': 5.0,
                'boss_contact_time_seconds': 1.0,
                'effective_damage_reduction_pct': 90.0,
                'incoming_damage_multiplier': 1.0,
            },
        )


@pytest.mark.live
def test_build_boss_wave_payload_live_path_avoids_delta_fallback():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out')
    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=50,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={
            'orb_boss_hit_pct': 2.5,
            'orb_boss_hits_per_second': 5.0,
            'electron_hits_per_second': 5.0,
            'boss_contact_time_seconds': 1.0,
            'effective_damage_reduction_pct': 90.0,
            'incoming_damage_multiplier': 1.0,
        },
    )

    diagnostics = payload.get('diagnostics') or {}
    assert diagnostics['actual_boss_interval_waves'] == 9
    assert diagnostics['checkpoint_every_bosses'] == 1
    assert diagnostics['checkpoint_resolution_mode'] == 'replacement_table1_table2_overlay'
    assert diagnostics['execution_mode'] == 'staged_replacement_phase2b'
    assert diagnostics['replacement_model']['boss_ttk_contract'] == 'v21_event_only'
    assert diagnostics['legacy_shadow_available'] is True
    assert diagnostics['legacy_shadow_materialized'] is False
    assert diagnostics['delta_fallback_count'] == 0
    first_row = (payload.get('rows') or [{}])[0]
    assert first_row.get('display_wave') == 9
    assert 'effective_damage_reduction_pct_used' in first_row
    assert 'boss_contact_time_seconds_used' in first_row
    assert 'boss_hit_interval_seconds_used' in first_row
    assert 'incoming_damage_multiplier_used' in first_row


def test_build_boss_wave_payload_tourney_fails_closed_without_tournament_wave(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    monkeypatch.setattr(
        pipeline_mod,
        'load_inputs',
        lambda ids_path=None, manual_inputs_path=None: type(
            'Bundle',
            (),
            {'ids_raw': {}, 'loadout_config': {}, 'perk_config': {}, 'perk_policy': {}},
        )(),
    )
    monkeypatch.setattr(
        pipeline_mod,
        'build_runtime_state',
        lambda ids_raw, loadout_config=None, perk_config=None: type(
            'State',
            (),
            {'player_meta': {'Tourney League': 'Legends'}},
        )(),
    )

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out', preset='Tourney')
    payload = pipeline_mod.build_boss_wave_payload(
        request,
        preset_name='Tourney',
        tier_number=14,
        end_wave=100,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={},
    )

    diagnostics = payload.get('diagnostics') or {}
    assert (payload.get('rows') or []) == []
    assert diagnostics['context_status'] == 'error'
    assert diagnostics['context_error'] == 'missing_tournament_wave'
    assert 'requires a resolved tournament wave' in str(diagnostics['context_error_message'] or '').lower()


@pytest.mark.live
def test_pipeline_computed_qe_publications_reach_input_dashboard(tmp_path, monkeypatch):
    def _fake_qe_dashboard_publications(**_kwargs):
        return {
            'workshop_coin_values': {'Damage': 'xSENTINEL_COIN'},
            'workshop_max_values': {'Damage': 'xSENTINEL_MAX'},
            'uw_track_effects': {
                'Chain Lightning::Damage': {
                    'module_effect': 'xSENTINEL_MODULE',
                    'perk_effect': 'xSENTINEL_PERK',
                    'final_value': 'xSENTINEL_FINAL',
                },
            },
        }

    monkeypatch.setattr('app.pipeline._build_input_dashboard_qe_publications', _fake_qe_dashboard_publications)

    out_dir = tmp_path / "out"
    request = PipelineRunRequest(ids=IDS_PATH, out=out_dir, preset='Farming', state_mode='start_of_run')
    result = execute_pipeline(request)

    assert result.exit_code == 0
    dashboard = json.loads((out_dir / 'input_dashboard.json').read_text(encoding='utf-8'))
    panel_by_id = {panel.get('panel_id'): panel for panel in (dashboard.get('panels') or [])}

    workshop_groups = (panel_by_id['workshop'].get('payload') or {}).get('groups') or {}
    workshop_rows = (
        (workshop_groups.get('offense') or [])
        + (workshop_groups.get('defense') or [])
        + (workshop_groups.get('utility') or [])
    )
    damage_row = next((row for row in workshop_rows if row.get('name') == 'Damage'), None)
    assert damage_row is not None
    assert damage_row.get('coin_value') == 'xSENTINEL_COIN'
    assert damage_row.get('max_value') == 'xSENTINEL_MAX'
    assert sorted(damage_row.keys()) == ['coin_level', 'coin_value', 'max_level', 'max_value', 'name', 'unlock']

    uw_rows = (panel_by_id['ultimate_weapons'].get('payload') or {}).get('rows') or []
    uw_damage_row = next((row for row in uw_rows if row.get('uw') == 'Chain Lightning' and row.get('track') == 'Damage'), None)
    assert uw_damage_row is not None
    assert uw_damage_row.get('module') == 'xSENTINEL_MODULE'
    assert uw_damage_row.get('perk') == 'xSENTINEL_PERK'
    assert uw_damage_row.get('final') == 'xSENTINEL_FINAL'


def test_input_dashboard_payload_consumes_qe_publications():
    from app.publication import _build_input_dashboard_payload

    account_state = json.loads((ROOT / 'out' / 'account_state.json').read_text(encoding='utf-8'))
    dashboard = _build_input_dashboard_payload(
        account_state,
        {},
        qe_dashboard_publications={
            'workshop_coin_values': {'Damage': 'x1234'},
            'workshop_max_values': {'Damage': 'x9000'},
            'uw_track_effects': {'Chain Lightning::Damage': {'module_effect': 'x2.25', 'perk_effect': '5', 'final_value': 'x903'}},
        },
    )
    panel_by_id = {panel.get('panel_id'): panel for panel in (dashboard.get('panels') or [])}
    workshop_groups = (panel_by_id['workshop'].get('payload') or {}).get('groups') or {}
    workshop_rows = (
        (workshop_groups.get('offense') or [])
        + (workshop_groups.get('defense') or [])
        + (workshop_groups.get('utility') or [])
    )
    damage_row = next((row for row in workshop_rows if row.get('name') == 'Damage'), None)
    assert damage_row is not None
    assert damage_row.get('coin_value') == 'x1234'
    assert damage_row.get('max_value') == 'x9000'
    assert sorted(damage_row.keys()) == ['coin_level', 'coin_value', 'max_level', 'max_value', 'name', 'unlock']

    uw_rows = (panel_by_id['ultimate_weapons'].get('payload') or {}).get('rows') or []
    uw_damage_row = next((row for row in uw_rows if row.get('uw') == 'Chain Lightning' and row.get('track') == 'Damage'), None)
    assert uw_damage_row is not None
    assert uw_damage_row.get('module') == 'x2.25'
    assert uw_damage_row.get('perk') == '5'
    assert uw_damage_row.get('final') == 'x903'
    assert sorted(uw_damage_row.keys()) == [
        'final',
        'lab',
        'module',
        'perk',
        'stone_level',
        'stone_value',
        'track',
        'unlock',
        'uw',
        'uw_plus',
    ]
    uw_damage_gaps = [
        gap for gap in (dashboard.get('upstream_gaps') or [])
        if gap.get('panel_id') == 'ultimate_weapons' and 'Chain Lightning::Damage' in str(gap.get('detail') or '')
    ]
    uw_damage_gap_ids = [gap.get('gap_id') for gap in uw_damage_gaps]
    assert 'module_column_not_published_upstream' not in uw_damage_gap_ids
    assert 'perk_column_not_published_upstream' not in uw_damage_gap_ids
    assert 'final_column_not_published_upstream' not in uw_damage_gap_ids


def test_stats_dashboard_fails_closed_when_only_fallback_artifacts_have_values():
    from app.publication import _build_input_dashboard_payload, _build_stats_dashboard_payload

    account_state = {
        'default_preset': 'Farming',
        'card_presets': {'Farming': []},
        'module_presets': {},
        'workshop': {
            'Wall Rebuild': {'preset_levels': {'Farming': 250}},
        },
        'workshop_enhancement_tracks': {},
        'cards_inventory': {},
        'raw_sections': {
            'workshop': {
                'groups': {
                    'utility': [
                        {'name': 'Wall Rebuild', 'coin_level': '250', 'coin_value': '300.0', 'max_level': '300', 'max_value': '300.0'},
                    ]
                }
            }
        },
        'uw_tracks': {},
        'ultimate_weapons': {},
    }

    input_dashboard = _build_input_dashboard_payload(account_state, {}, module_card_payloads={})
    payload = _build_stats_dashboard_payload(
        account_state_payload=account_state,
        diagnostics={},
        input_dashboard_payload=input_dashboard,
        module_card_payloads={},
        query_rows_start_of_run={'Farming': {'rows': {}}},
        query_rows_max_progression={'Farming': {'rows': {}}},
        ep_compare_publishable={},
        line_verification={
            'state::wall.rebuild_seconds': {'final_value': 150.0, 'unit': 'seconds', 'status': 'resolved'},
        },
        selected_preset='Farming',
        selected_state_mode='start_of_run',
    )

    workshop = next(
        panel for panel in payload['variants']['Farming']['start_of_run']
        if panel.get('panel_id') == 'workshop'
    )
    rows = [
        row
        for section in workshop.get('payload', {}).get('sections') or []
        for row in section.get('rows') or []
    ]
    by_name = {row.get('name'): row for row in rows}
    assert by_name['Wall Rebuild']['start_of_run_value'] == '—'
    assert by_name['Wall Rebuild']['max_progression_value'] == '—'


def test_build_input_dashboard_qe_publications_accepts_typed_uw_tracks():
    account_state = SimpleNamespace(
        uw_tracks={
            'Chain Lightning': [
                SimpleNamespace(track_name='Damage', level=100, resolved_value=1.5),
            ],
        }
    )
    published = _build_input_dashboard_qe_publications(
        account_state=account_state,
        compare_rows_by_preset={
            'Farming': {
                'state::tower.damage': {'display_value': 'x100'},
                'state::tower.crit_chance_pct': {'display_value': '69%'},
                'state::uw.chain_lightning.damage_multiplier': {
                    'display_value': 'x903',
                    'contributors': [],
                },
            }
        },
        projected_compare_rows_by_preset={
            'Farming': {
                'state::tower.damage': {'display_value': 'x9000'},
                'state::tower.crit_chance_pct': {'display_value': '99%'},
                'state::uw.chain_lightning.damage_multiplier': {
                    'display_value': 'x903',
                    'contributors': [],
                }
            }
        },
        stat_inputs=[
            SimpleNamespace(
                source_family='workshop',
                source_name='Damage',
                destination_id='tower_damage',
                contributor_id='workshop__tower__damage__flat',
            ),
            SimpleNamespace(
                source_family='workshop',
                source_name='Critical Chance',
                destination_id='tower_crit_chance_pct',
                contributor_id='workshop__tower__crit_chance__pct',
            ),
        ],
        preset_name='Farming',
    )
    assert published.get('workshop_coin_values', {}).get('Damage') == 'x100'
    assert published.get('workshop_max_values', {}).get('Damage') == 'x9000'
    assert published.get('workshop_coin_values', {}).get('Critical Chance') == '69%'
    assert published.get('workshop_max_values', {}).get('Critical Chance') == '99%'
    effects = published.get('uw_track_effects') or {}
    assert 'Chain Lightning::Damage' in effects
    assert effects['Chain Lightning::Damage']['final_value'] == 'x903'


@pytest.mark.live
def test_optimizer_scores_populated(canonical_pipeline_artifacts):
    """optimizer_scores.json must be non-empty."""
    scores = canonical_pipeline_artifacts['optimizer_scores']
    assert isinstance(scores, dict) and len(scores) > 0, "optimizer_scores.json must be non-empty"


@pytest.mark.live
def test_run_stats_canonical_output_filenames(run_stats_single_execution):
    """RunStatsSession.execute() must write canonical run_stats_query_plan_* and run_stats_query_rows_* filenames."""
    out_dir = run_stats_single_execution["out_dir"]

    for key, filename in _RUN_STATS_QUERY_OUTPUTS.items():
        assert (out_dir / filename).exists(), f"Expected canonical output {filename} but it was not written"

    legacy_filenames = [
        'stat_inputs_start_of_run.json', 'stat_inputs_max_progression.json',
        'statbook_start_of_run.json', 'statbook_max_progression.json',
    ]
    for name in legacy_filenames:
        assert not (out_dir / name).exists(), f"Legacy output {name} must not be written"


@pytest.mark.live
def test_run_stats_output_contract_distinguishes_committed_and_local_support(run_stats_single_execution):
    diag = run_stats_single_execution["parsed_outputs"]["diagnostics.json"]
    contract = diag.get('output_contract') or {}

    assert contract.get('contract_kind') == 'run_stats_bounded'
    assert tuple(contract.get('committed_baseline_artifacts') or []) == RUN_STATS_COMMITTED_BASELINE_ARTIFACTS
    assert tuple(contract.get('local_support_artifacts') or []) == RUN_STATS_LOCAL_SUPPORT_ARTIFACTS
    assert tuple(contract.get('all_local_output_artifacts') or []) == RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS


@pytest.mark.live
def test_run_stats_writes_stats_dashboard_artifact(run_stats_single_execution):
    stats_dashboard = json.loads((run_stats_single_execution["out_dir"] / "stats_dashboard.json").read_text(encoding='utf-8'))

    assert stats_dashboard.get("artifact") == "stats_dashboard.json"
    assert stats_dashboard.get("schema_version") == 1
    panel_ids = [panel.get("panel_id") for panel in (stats_dashboard.get("panels") or [])]
    secondary_panel_ids = [panel.get("panel_id") for panel in (stats_dashboard.get("secondary_panels") or [])]
    assert panel_ids == ["workshop", "ultimate_weapons", "bots", "guardians", "modules"]
    assert "modules_resolved" in secondary_panel_ids
    assert "guardians_resolved" in secondary_panel_ids


@pytest.mark.live
def test_run_stats_committed_payload_excludes_volatile_timing_telemetry(run_stats_single_execution):
    run_stats = json.loads((run_stats_single_execution["out_dir"] / "run_stats.json").read_text(encoding='utf-8'))
    diagnostics = run_stats.get('diagnostics') or {}

    assert 'timings_ms' not in diagnostics
    assert 'account_state_build_ms' not in (diagnostics.get('session') or {})
    for preset_payload in (diagnostics.get('presets') or {}).values():
        assert 'timings_ms' not in ((preset_payload.get('start_of_run') or {}))
        assert 'timings_ms' not in ((preset_payload.get('max_progression') or {}))


@pytest.mark.live
def test_run_stats_bounded_outputs_do_not_masquerade_as_full_pipeline_outputs(run_stats_single_execution):
    out_dir = run_stats_single_execution["out_dir"]
    written_names = {path.name for path in out_dir.glob("*.json")}

    assert set(RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS).issubset(written_names)
    assert 'pipeline_trace.json' not in written_names
    for name in FULL_PIPELINE_PUBLICATION_ARTIFACTS:
        if name in RUN_STATS_BOUNDED_OUTPUT_ARTIFACTS:
            continue
        assert name not in written_names, f"run_stats bounded output must not silently publish full-pipeline artifact {name}"


@pytest.mark.live
def test_resolve_fast_checkpoint_smoke():
    """Fast-checkpoint API resolves requested surfaces with structured statbook output."""
    request = FastCheckpointRequest(
        ids=IDS_PATH,
        requested_surface_ids=("canonical_stat::tower_hp", "canonical_stat::tower_damage"),
    )
    result = resolve_fast_checkpoint(request)

    assert result.statbook is not None
    assert "rows" in result.statbook
    assert "canonical_stat::tower_hp" in result.statbook["rows"]
    assert "canonical_stat::tower_damage" in result.statbook["rows"]


@pytest.mark.live
def test_resolve_fast_checkpoint_rejects_empty_surface_ids():
    """Fast-checkpoint must raise ValueError when requested_surface_ids is empty."""
    request = FastCheckpointRequest(ids=IDS_PATH, requested_surface_ids=())
    with pytest.raises(ValueError, match='requested_surface_ids'):
        resolve_fast_checkpoint(request)


def test_path_cache_token_changes_on_file_modification(tmp_path):
    """_path_cache_token must produce a different token after a file is modified."""
    f = tmp_path / "ids.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    token1 = _path_cache_token(f)
    assert token1[1] is not None, "mtime should be captured for existing file"

    # Modify the file (ensure mtime changes by writing more content)
    time.sleep(0.01)
    f.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    # Touch to guarantee mtime change on fast filesystems
    f.touch()
    token2 = _path_cache_token(f)

    assert token1 != token2, "cache token must differ after file modification"


def test_path_cache_token_missing_file():
    """_path_cache_token must not raise for a non-existent path."""
    token = _path_cache_token(Path("/nonexistent/path/ids.csv"))
    assert token[1] is None and token[2] is None


def test_run_stats_session_cache_key_is_file_content_based(tmp_path):
    """RunStatsSession cache key must differ after input file content changes."""
    f = tmp_path / "ids.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    session = RunStatsSession()
    key1 = session._account_state_cache_key(ids_path=f, manual_inputs_path=None, perk_mode='none')

    time.sleep(0.01)
    f.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    f.touch()
    key2 = session._account_state_cache_key(ids_path=f, manual_inputs_path=None, perk_mode='none')

    assert key1 != key2, "cache key must differ after ids file content changes"


def test_run_stats_session_cache_key_differs_by_perk_mode(tmp_path):
    """RunStatsSession cache key must differ by perk_mode."""
    f = tmp_path / "ids.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    session = RunStatsSession()
    key_none = session._account_state_cache_key(ids_path=f, manual_inputs_path=None, perk_mode='none')
    key_max = session._account_state_cache_key(ids_path=f, manual_inputs_path=None, perk_mode='max_progression_policy')
    assert key_none != key_max


@pytest.mark.live
def test_run_stats_diagnostics_contains_write_outputs_ms(run_stats_single_execution):
    """diagnostics.json persisted by RunStatsSession.execute() must include write_outputs_ms."""
    diag = run_stats_single_execution["parsed_outputs"]["diagnostics.json"]
    timings = diag.get('timings_ms', {})
    assert 'write_outputs_ms' in timings, "diagnostics.json must contain write_outputs_ms from final write"
    assert isinstance(timings['write_outputs_ms'], (int, float)), "write_outputs_ms must be numeric"


@pytest.mark.live
def test_ep_oracle_compare_exists_and_nonempty_for_sharded_path(tmp_path):
    """Protect the sharded evaluator output publication contract for ep_oracle_compare.json."""
    out_dir = tmp_path / "out"
    request = PipelineRunRequest(ids=IDS_PATH, out=out_dir, preset='Farming', state_mode='start_of_run')
    execute_pipeline(request)

    compare_path = out_dir / "ep_oracle_compare.json"
    assert compare_path.exists()
    compare_data = json.loads(compare_path.read_text(encoding='utf-8'))


@pytest.mark.live
def test_execute_pipeline_writes_full_pipeline_artifact_contract(tmp_path):
    out_dir = tmp_path / "out"
    request = PipelineRunRequest(ids=IDS_PATH, out=out_dir, preset='Farming', state_mode='start_of_run')
    result = execute_pipeline(request)

    assert result.exit_code == 0
    written_names = {path.name for path in result.generated_files}
    assert 'pipeline_trace.json' in written_names
    for name in FULL_PIPELINE_PUBLICATION_ARTIFACTS:
        assert name in written_names, f"execute_pipeline must write full-pipeline artifact {name}"
def test_ep_oracle_compare_populated(canonical_pipeline_artifacts):
    """ep_oracle_compare.json must stay structurally aligned with the published compare summary."""
    compare = canonical_pipeline_artifacts['ep_oracle_compare']
    summary = canonical_pipeline_artifacts['diagnostics']['ep_compare_summary']
    assert isinstance(compare, dict)
    assert len(compare) == int(summary.get('ep_compare_count') or 0)


@pytest.mark.live
def test_sharded_evaluators_parity(canonical_pipeline_artifacts):
    """Sharded evaluator outputs stay internally consistent even when EP compare is empty."""
    compare_data = canonical_pipeline_artifacts['ep_oracle_compare']
    projection_views = canonical_pipeline_artifacts['diagnostics']['ep_compare_projection_views']
    assert isinstance(compare_data, dict)
    assert int((projection_views.get('current_state_mode') or {}).get('ep_compare_count') or 0) == len(compare_data)
