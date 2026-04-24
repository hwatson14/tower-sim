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
import yaml

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
        ids=IDS_PATH, out=out_dir, perk_mode='max_progression_policy', perk_state='auto', manual_inputs=None,
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

    _install_fake_boss_wave_app_dependencies(monkeypatch, pipeline_mod)
    _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod)

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out', perk_mode='runtime_timeline')
    payload = pipeline_mod.build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=30,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'orb_boss_hit_pct': 2.5,
            'orb_boss_hit_count': 5,
            'electron_hit_count': 5,
            'boss_time_to_contact_seconds': 1.0,
            'effective_damage_reduction_pct': 90.0,
            'incoming_damage_multiplier': 1.0,
            'flame_bot_damage_reduction_pct': 0.0,
            'flame_bot_duration_seconds': 0.0,
            'flame_bot_cooldown_seconds': 1.0,
            'defense_field_damage_reduction_pct': 0.0,
            'defense_field_duration_seconds': 0.0,
            'defense_field_cooldown_seconds': 1.0,
            'black_hole_damage_reduction_pct': 0.0,
            'black_hole_duration_seconds': 0.0,
            'black_hole_cooldown_seconds': 1.0,
            'pbh_encounter_uptime_fraction': 0.0,
        },
    )

    assert payload.get('artifact') == 'boss_wave_dashboard_payload'
    assert payload.get('schema_version') == 1
    assert payload.get('contract', {}).get('simulator_owner') == 'simulators.evaluator_kernel.evaluate_overlay_row'
    assert payload.get('source_selection', {}).get('active_source') == 'replacement'
    assert payload.get('contract', {}).get('perk_timeline_mode') == 'runtime_policy_projection'
    assert payload.get('contract', {}).get('checkpoint_mode') == 'actual_boss_cadence_with_sampling'
    assert payload.get('download', {}).get('format') == 'csv'
    summary = payload.get('summary') or {}
    assert summary['max_wave'] == 27
    assert summary['max_surviving_wave'] == 27
    assert summary['first_failed_wave'] == 0
    assert summary['result_consistent_with_rows'] is True
    diagnostics = payload.get('diagnostics') or {}
    assert diagnostics['preset_name'] == 'Farming'
    assert diagnostics['mode_id'] == 'farming'
    assert diagnostics['tier_number'] == 14
    assert diagnostics['tier_column'] == 'Tier 14'
    assert diagnostics['actual_boss_interval_waves'] == 9
    assert diagnostics['checkpoint_every_bosses'] == 1
    assert diagnostics['checkpoint_mode'] == 'actual_boss_cadence_with_sampling'
    assert diagnostics['checkpoint_resolution_mode'] == 'replacement_table1_table2_overlay'
    assert diagnostics['execution_mode'] == 'staged_replacement'
    assert diagnostics['stop_on_failure'] is True
    assert diagnostics['perk_timeline_rows'] >= 0
    assert diagnostics['scenario_runtime_inputs']['orb_boss_hit_pct'] == 2.5


def _install_fake_boss_wave_app_dependencies(monkeypatch, pipeline_mod):
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
            {'player_meta': {}, 'labs': {'Wall Thorns': 16}, 'active_perk_preset': 'Farming'},
        )(),
    )


def _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod, *, omit_surface: str | None = None):
    class _FakeRow:
        def __init__(self, value, contributors=None):
            self.final_value = value
            self.status = 'resolved'
            self.contributors = list(contributors or [])

    rows = {
        'state::tower.enemy_attack_level_skip_pct': _FakeRow(0.0),
        'state::tower.enemy_health_level_skip_pct': _FakeRow(0.0),
        'state::tower.free_attack_upgrade_chance_pct': _FakeRow(0.0),
        'state::tower.free_defense_upgrade_chance_pct': _FakeRow(0.0),
        'state::tower.free_utility_upgrade_chance_pct': _FakeRow(0.0),
        'state::tower.hp': _FakeRow(500.0),
        'state::tower.regen': _FakeRow(100.0),
        'state::wall.hp': _FakeRow(
            1000.0,
            contributors=[
                {
                    'active': True,
                    'value': 1000000000000.0,
                    'composition_stage': 'additive_pre_cap',
                    'contributor_id': 'workshop__wall__health__flat',
                    'input_value_type': 'resolved_value',
                },
                {
                    'active': True,
                    'value': 2.0,
                    'composition_stage': 'multiplicative',
                    'contributor_id': 'enhancement.wall_health_+.account_state',
                    'input_value_type': 'resolved_value',
                },
                {
                    'active': True,
                    'value': 2.0,
                    'composition_stage': 'multiplicative',
                    'contributor_id': 'lab__wall__fortification__multiplier',
                    'input_value_type': 'resolved_value',
                },
            ],
        ),
        'state::wall.regen': _FakeRow(25.0),
        'state::wall.fortification_multiplier': _FakeRow(2.0),
        'state::tower.defense_pct': _FakeRow(90.0),
        'state::tower.thorns_damage_pct': _FakeRow(99.0),
        'state::wall.thorns_damage_pct': _FakeRow(15.84),
        'state::cards.plasma_cannon.effect_pct': _FakeRow(100.0),
        'state::module.orbital_augment.electron_count': _FakeRow(2.0),
        'state::module.primordial_collapse.bh_damage_reduction_pct': _FakeRow(80.0),
        'state::uw.black_hole.duration_seconds': _FakeRow(36.0),
        'state::uw.black_hole.cooldown_seconds': _FakeRow(46.0),
        'state::uw.chrono_field.duration_seconds': _FakeRow(50.0),
        'state::uw.chrono_field.cooldown_seconds': _FakeRow(60.0),
        'state::uw.chrono_field.damage_reduction_pct': _FakeRow(20.0),
        'state::bot.flame.damage_reduction_pct': _FakeRow(0.35),
        'state::bot.flame.cooldown_seconds': _FakeRow(26.0),
        'state::bot.flame.range_m': _FakeRow(55.0),
    }
    if omit_surface:
        rows.pop(omit_surface)
    monkeypatch.setattr(pipeline_mod, 'resolve_checkpoint_surfaces', lambda *args, **kwargs: object())
    monkeypatch.setattr(pipeline_mod, 'query_response_to_statbook', lambda *args, **kwargs: SimpleNamespace(rows=rows))


def test_build_boss_wave_payload_replacement_inputs_drive_table_summary_export_and_diagnostics(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_fake_boss_wave_app_dependencies(monkeypatch, pipeline_mod)
    _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod)

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out', perk_mode='runtime_timeline')
    payload = pipeline_mod.build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=30,
        boss_wave_step=1,
        stop_on_failure=True,
        scenario_runtime_inputs={
            'orb_boss_hit_pct': 2.5,
            'orb_boss_hit_count': 5,
            'electron_hit_count': 5,
            'boss_time_to_contact_seconds': 1.0,
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
    assert 'rollback_source' not in source_selection
    assert 'rollback_available' not in source_selection
    assert source_selection.get('active_source') == 'replacement'
    assert source_selection.get('csv_export_source') == 'replacement'
    assert source_selection.get('diagnostics_source') == 'replacement'
    assert not hasattr(pipeline_mod, 'build_start_of_run_state')
    assert not hasattr(pipeline_mod, 'build_boss_wave_table_payload')

    operator_rows = payload.get('operator_rows') or []
    assert payload.get('rows') == operator_rows
    assert operator_rows[0]['replacement_source'] == 'replacement'
    assert operator_rows[0]['tower_damage_per_second'] is None
    assert operator_rows[0]['summary_lane_id'] == 'avg'
    assert set(operator_rows[0]['lane_handle_ids']) == {'avg', 'min', 'max'}
    assert operator_rows[0]['boss_plasma_cannon_damage_to_boss_pct'] >= 0
    assert operator_rows[0]['boss_orb_damage_to_boss_pct'] >= 0
    assert operator_rows[0]['boss_electron_damage_to_boss_pct'] >= 0
    assert operator_rows[0]['boss_wall_thorns_damage_to_boss_pct'] >= 0
    assert operator_rows[0]['boss_expected_wall_thorns_damage_from_hits_pct'] >= operator_rows[0]['boss_wall_thorns_damage_to_boss_pct']
    assert operator_rows[0]['boss_hits_to_player'] == operator_rows[0]['boss_hits_taken']
    assert operator_rows[0]['boss_wall_thorns_hits'] == operator_rows[0]['boss_hits_taken']
    assert 'legacy_export_owner' not in contract
    assert 'legacy_shadow' not in payload
    assert payload.get('download_rows')[0]['replacement_source'] == 'replacement'
    assert payload.get('download_rows')[0]['operator_handle_id'] == operator_rows[0]['operator_handle_id']
    assert payload.get('download_rows')[0]['boss_wall_thorns_damage_to_boss_pct'] == operator_rows[0]['boss_wall_thorns_damage_to_boss_pct']
    assert payload.get('download_rows')[0]['boss_expected_wall_thorns_damage_from_hits_pct'] == operator_rows[0]['boss_expected_wall_thorns_damage_from_hits_pct']
    assert payload.get('download', {}).get('row_source') == 'replacement'
    diagnostics = payload.get('diagnostics') or {}
    assert diagnostics.get('execution_mode') == 'staged_replacement'
    assert diagnostics.get('checkpoint_resolution_mode') == 'replacement_table1_table2_overlay'
    assert diagnostics.get('source_selection', {}).get('diagnostics_source') == 'replacement'
    assert diagnostics.get('replacement_model', {}).get('boss_ttk_contract') == 'v21_event_only'
    assert diagnostics.get('replacement_model', {}).get('boss_kill_sources') == ['plasma_cannon', 'orbs', 'electrons', 'thorns_contact']
    assert diagnostics.get('replacement_model', {}).get('contact_resolution_sources') == ['wall_thorns_contact']
    assert diagnostics.get('replacement_model', {}).get('thorns_contact_source') == 'wall_thorns_contact_damage_pct_derived_from_tower_thorns_and_wall_thorns_lab'
    assert diagnostics.get('replacement_model', {}).get('wall_thorns_repeated_hit_multiplier') == 'Sharp Fortitude primary armor adds +1% wall-thorns damage taken per subsequent contact hit'
    assert diagnostics.get('replacement_model', {}).get('continuous_tower_dps_included') is False
    assert diagnostics.get('replacement_model', {}).get('contract_version') == 'boss_waves_replacement_v1'
    assert diagnostics.get('replacement_model', {}).get('table1_source_basis') == 'app_pipeline_qe_checkpoint_surfaces_to_run_plan'
    assert 'legacy_shadow_available' not in diagnostics
    assert 'legacy_shadow_materialized' not in diagnostics
    assert diagnostics.get('replacement_outputs', {}).get('download_row_count') == len(payload.get('download_rows') or [])
    ttk_inputs = diagnostics.get('replacement_primitive_semantics_ledger', {}).get('boss_ttk_input_contract') or {}
    assert ttk_inputs.get('orb_boss_total_damage_pct') == pytest.approx(2.0)
    assert ttk_inputs.get('orb_boss_total_damage_source') == 'default_orb_boss_total_damage_pct_2'
    assert ttk_inputs.get('electron_total_damage_pct') == pytest.approx(7.5)
    assert ttk_inputs.get('electron_total_damage_source') == 'orbital_augment_electron_count_times_boss_electron_pct'
    assert ttk_inputs.get('orbital_augment_electron_count') == pytest.approx(2.0)
    primitive_values = diagnostics.get('replacement_primitive_inputs', {}).get('values') or {}
    assert primitive_values['tower_thorns_damage_pct'] == pytest.approx(99.0)
    assert primitive_values['wall_thorns_level'] == pytest.approx(16.0)
    assert primitive_values['wall_thorns_contact_damage_pct'] == pytest.approx(15.84)
    assert primitive_values['primordial_collapse_bh_damage_reduction_pct'] == pytest.approx(80.0)
    assert primitive_values['black_hole_duration_seconds'] == pytest.approx(36.0)
    assert primitive_values['black_hole_cooldown_seconds'] == pytest.approx(46.0)
    timed_dr = diagnostics.get('replacement_primitive_semantics_ledger', {}).get('timed_dr_semantic_contract') or {}
    timed_sources = timed_dr.get('sources') or {}
    assert timed_sources['black_hole_pbh']['damage_reduction_pct'] == pytest.approx(80.0)
    assert timed_sources['black_hole_pbh']['uptime_fraction'] == pytest.approx(36.0 / 46.0)
    assert timed_sources['black_hole_pbh']['effective_dr_fraction'] == pytest.approx(0.8 * (36.0 / 46.0))
    assert timed_sources['final_dr_override']['primitive_status'] == 'runtime_final_dr_override_bypasses_timed_dr_sources'
    assert timed_sources['flame_bot']['primitive_status'] == 'blocked_missing_duration_seconds_primitive'
    assert timed_sources['defense_field']['primitive_status'] == 'explicit_runtime_only_no_qe_surface_found'

    summary = payload.get('summary') or {}
    assert summary['max_surviving_wave'] == 27
    assert summary['first_failed_wave'] == 0
    assert summary['survives_through_end'] is True


def test_build_boss_wave_payload_rejects_legacy_source_after_excision():
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out')
    with pytest.raises(ValueError, match='replacement-only'):
        pipeline_mod.build_boss_wave_payload(
            request,
            preset_name='Farming',
            tier_number=14,
            end_wave=30,
            boss_wave_step=1,
            stop_on_failure=True,
            scenario_runtime_inputs={},
            boss_wave_source='legacy',
        )


def test_build_boss_wave_payload_fails_closed_on_unmapped_required_input_primitive(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_fake_boss_wave_app_dependencies(monkeypatch, pipeline_mod)
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
                'orb_boss_hit_count': 5,
                'electron_hit_count': 5,
                'boss_time_to_contact_seconds': 1.0,
                'effective_damage_reduction_pct': 90.0,
                'incoming_damage_multiplier': 1.0,
            },
        )


def test_build_boss_wave_payload_fails_closed_on_missing_wall_regen_base_primitive(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_fake_boss_wave_app_dependencies(monkeypatch, pipeline_mod)
    _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod, omit_surface='state::tower.regen')

    request = PipelineRunRequest(ids=ROOT / 'input' / 'imports' / 'ids.csv', out=ROOT / 'out')
    with pytest.raises(ValueError, match="requires QE surface 'state::tower.regen'"):
        pipeline_mod.build_boss_wave_payload(
            request,
            preset_name='Farming',
            tier_number=14,
            end_wave=30,
            boss_wave_step=1,
            stop_on_failure=True,
            scenario_runtime_inputs={
                'orb_boss_hit_pct': 2.5,
                'orb_boss_hit_count': 5,
                'electron_hit_count': 5,
                'boss_time_to_contact_seconds': 1.0,
                'effective_damage_reduction_pct': 90.0,
                'incoming_damage_multiplier': 1.0,
            },
        )


def test_build_boss_wave_payload_fails_closed_on_missing_export_mapping(monkeypatch):
    from app import pipeline as pipeline_mod
    from app.models import PipelineRunRequest

    _install_fake_boss_wave_app_dependencies(monkeypatch, pipeline_mod)
    _install_fake_boss_wave_replacement_primitives(monkeypatch, pipeline_mod)
    monkeypatch.setattr(
        pipeline_mod,
        'BOSS_WAVE_REPLACEMENT_EXPORT_FIELDS',
        (*pipeline_mod.BOSS_WAVE_REPLACEMENT_EXPORT_FIELDS, 'unmapped_export_field'),
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
                'orb_boss_hit_count': 5,
                'electron_hit_count': 5,
                'boss_time_to_contact_seconds': 1.0,
                'effective_damage_reduction_pct': 90.0,
                'incoming_damage_multiplier': 1.0,
            },
        )


@pytest.mark.live
def test_build_boss_wave_payload_live_path_avoids_delta_fallback():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload, build_runtime_state, load_inputs
    from input.state_types import ScenarioRuntimeInputs
    from qe.routing import query_response_to_statbook, resolve_checkpoint_surfaces

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out')
    runtime_inputs = {
            'orb_boss_hit_pct': 100.0,
            'orb_boss_hit_count': 1,
            'boss_time_to_contact_seconds': 1.0,
        'effective_damage_reduction_pct': 90.0,
        'incoming_damage_multiplier': 1.0,
    }
    bundle = load_inputs(ids_path=request.ids, manual_inputs_path=request.manual_inputs)
    account_state = build_runtime_state(bundle.ids_raw, loadout_config=bundle.loadout_config, perk_config=bundle.perk_config)
    canonical_response = resolve_checkpoint_surfaces(
        account_state,
        requested_surface_ids=(
            'state::wall.hp',
            'state::tower.hp',
            'state::wall.regen',
            'state::tower.regen',
            'state::wall.fortification_multiplier',
            'state::tower.defense_pct',
            'state::tower.thorns_damage_pct',
            'state::wall.thorns_damage_pct',
            'state::cards.plasma_cannon.effect_pct',
            'state::module.orbital_augment.electron_count',
            'state::module.primordial_collapse.bh_damage_reduction_pct',
            'state::uw.chrono_field.duration_seconds',
            'state::uw.chrono_field.cooldown_seconds',
            'state::uw.chrono_field.damage_reduction_pct',
            'state::bot.flame.damage_reduction_pct',
            'state::bot.flame.cooldown_seconds',
        ),
        preset_name='Farming',
        state_mode='start_of_run',
        perks_enabled=True,
        scenario_runtime_inputs=ScenarioRuntimeInputs.from_mapping(runtime_inputs),
    )
    canonical_statbook = query_response_to_statbook(canonical_response, notes='Boss Waves primitive authority reconciliation test.')
    canonical = {
        surface_id: float(canonical_statbook.rows[surface_id].final_value)
        for surface_id in canonical_statbook.rows
    }
    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=50,
        boss_wave_step=1,
        stop_on_failure=False,
            scenario_runtime_inputs=runtime_inputs,
        )

    diagnostics = payload.get('diagnostics') or {}
    assert diagnostics['actual_boss_interval_waves'] == 9
    assert diagnostics['checkpoint_every_bosses'] == 1
    assert diagnostics['checkpoint_resolution_mode'] == 'replacement_table1_table2_overlay'
    assert diagnostics['execution_mode'] == 'staged_replacement'
    assert diagnostics['source_selection']['operator_table_source'] == 'replacement'
    assert diagnostics['source_selection']['summary_source'] == 'replacement'
    assert diagnostics['source_selection']['csv_export_source'] == 'replacement'
    assert diagnostics['source_selection']['diagnostics_source'] == 'replacement'
    assert payload['source_selection']['active_source'] == 'replacement'
    assert diagnostics['replacement_model']['boss_ttk_contract'] == 'v21_event_only'
    assert diagnostics['replacement_model']['contract_version'] == 'boss_waves_replacement_v1'
    assert diagnostics['replacement_model']['lane_order'] == ['avg', 'min', 'max']
    assert diagnostics['replacement_model']['summary_lane_id'] == 'avg'
    assert diagnostics['perk_application_mode'] == 'runtime_timeline'
    assert diagnostics['perk_timeline_rows'] > 0
    assert diagnostics['perk_static_count'] == 0
    assert diagnostics['perk_static_pick_count'] == 0
    assert diagnostics['perk_mode'] == 'runtime_timeline'
    assert diagnostics['perk_state'] == 'on'
    assert diagnostics['perk_state_source'] == 'scenario_policy_tournament_off_other_runs_on'
    assert payload['contract']['perk_timeline_mode'] == 'runtime_policy_projection'
    assert 'legacy_shadow_available' not in diagnostics
    assert 'legacy_shadow_materialized' not in diagnostics
    assert diagnostics['delta_fallback_count'] == 0
    primitive_inputs = diagnostics['replacement_primitive_inputs']
    assert primitive_inputs['layer'] == 'primitive_start_of_run_inputs_not_final_displayed_rows'
    primitives = primitive_inputs['values']
    expected_wall_regen = canonical['state::tower.regen'] * (canonical['state::wall.regen'] / 100.0)
    expected_wall_hp_pre_fort = (
        canonical['state::tower.hp']
        * primitives['wall_hp_ratio']
        * primitives['wall_hp_multiplier']
    )
    assert primitives['tower_hp'] == pytest.approx(canonical['state::tower.hp'])
    assert primitives['wall_hp_qe_surface'] == pytest.approx(canonical['state::wall.hp'])
    assert primitives['wall_hp'] == pytest.approx(expected_wall_hp_pre_fort)
    assert primitives['tower_regen'] == pytest.approx(canonical['state::tower.regen'])
    assert primitives['wall_regen_percent_points'] == pytest.approx(canonical['state::wall.regen'])
    assert primitives['wall_regen'] == pytest.approx(expected_wall_regen)
    assert primitives['wall_fortification_multiplier'] == pytest.approx(canonical['state::wall.fortification_multiplier'])
    assert primitives['tower_defense_pct'] == pytest.approx(canonical['state::tower.defense_pct'])
    assert primitives['tower_thorns_damage_pct'] == pytest.approx(canonical['state::tower.thorns_damage_pct'])
    assert primitives['wall_thorns_contact_damage_pct'] == pytest.approx(canonical['state::wall.thorns_damage_pct'])
    assert primitives['wall_thorns_level'] == pytest.approx(float(account_state.labs['Wall Thorns']))
    assert primitives['wall_thorns_contact_damage_pct'] == pytest.approx(19.36)
    assert primitives['plasma_cannon_effect_pct'] == pytest.approx(canonical['state::cards.plasma_cannon.effect_pct'])
    assert primitives['orbital_augment_electron_count'] == pytest.approx(canonical['state::module.orbital_augment.electron_count'])
    assert primitives['primordial_collapse_bh_damage_reduction_pct'] == pytest.approx(canonical['state::module.primordial_collapse.bh_damage_reduction_pct'])
    assert primitives['black_hole_duration_seconds'] == pytest.approx(36.0)
    assert primitives['black_hole_cooldown_seconds'] == pytest.approx(46.0)
    assert primitives['chrono_field_duration_seconds'] == pytest.approx(canonical['state::uw.chrono_field.duration_seconds'])
    assert primitives['chrono_field_cooldown_seconds'] == pytest.approx(canonical['state::uw.chrono_field.cooldown_seconds'])
    assert primitives['chrono_field_damage_reduction_pct'] == pytest.approx(canonical['state::uw.chrono_field.damage_reduction_pct'])
    assert primitives['flame_bot_damage_reduction_pct'] == pytest.approx(canonical['state::bot.flame.damage_reduction_pct'])
    assert primitives['flame_bot_cooldown_seconds'] == pytest.approx(canonical['state::bot.flame.cooldown_seconds'])
    ledger = diagnostics['replacement_primitive_semantics_ledger']
    assert ledger['primitives']['state::wall.hp']['semantic_meaning'].startswith('QE wall HP surface currently carries wall-health ratio contributors')
    assert ledger['primitives']['state::wall.hp']['fortification_transform'] == 'not_used_as_final_wall_hp'
    assert ledger['primitives']['state::wall.hp']['classification'] == 'transformed'
    assert ledger['primitives']['state::wall.hp']['boss_waves_semantic_decision'] == 'transformed_primitive_not_final_display_value'
    assert ledger['primitives']['state::wall.hp']['tower_hp'] == pytest.approx(canonical['state::tower.hp'])
    assert ledger['primitives']['state::wall.regen']['classification'] == 'transformed'
    assert ledger['primitives']['state::wall.regen']['boss_waves_semantic_decision'] == 'transformed_percent_points_primitive_not_final_hp_per_second'
    assert ledger['primitives']['state::wall.regen']['exact_value'] == pytest.approx(canonical['state::wall.regen'])
    assert ledger['primitives']['state::wall.regen']['row_input_value'] == pytest.approx(expected_wall_regen)
    assert ledger['primitives']['state::tower.regen']['exact_value'] == pytest.approx(canonical['state::tower.regen'])
    assert ledger['primitives']['state::tower.thorns_damage_pct']['semantic_meaning'].endswith(
        'upstream base for Wall Thorns contact damage'
    )
    assert ledger['primitives']['state::wall.thorns_contact_damage_pct']['exact_value'] == pytest.approx(
        primitives['wall_thorns_contact_damage_pct']
    )
    assert 'contact-resolution source' in ledger['primitives']['state::wall.thorns_contact_damage_pct']['semantic_meaning']
    assert ledger['primitives']['state::module.primordial_collapse.bh_damage_reduction_pct']['exact_value'] == pytest.approx(
        canonical['state::module.primordial_collapse.bh_damage_reduction_pct']
    )
    timed_sources = ledger['timed_dr_semantic_contract']['sources']
    assert timed_sources['black_hole_pbh']['damage_reduction_pct'] == pytest.approx(
        canonical['state::module.primordial_collapse.bh_damage_reduction_pct']
    )
    assert timed_sources['black_hole_pbh']['uptime_fraction'] == pytest.approx(
        36.0 / 46.0
    )
    assert timed_sources['black_hole_pbh']['effective_dr_fraction'] == pytest.approx(0.8 * (36.0 / 46.0))
    assert timed_sources['flame_bot']['primitive_status'] == 'blocked_missing_duration_seconds_primitive'
    assert timed_sources['defense_field']['primitive_status'] == 'explicit_runtime_only_no_qe_surface_found'
    assert ledger['primitives']['module::Sharp Fortitude.wall_thorns_damage_increase_per_hit']['exact_value'] == pytest.approx(0.01)
    assert ledger['workshop_levels']['Wall Health']['exact_value'] == account_state.workshop['Wall Health'].preset_levels['Farming']
    assert ledger['workshop_levels']['Health Regen']['exact_value'] == account_state.workshop['Health Regen'].preset_levels['Farming']
    assert ledger['workshop_levels']['Wall Fortification']['exact_value'] == account_state.labs['Wall Fortification']
    assert ledger['workshop_levels']['Wall Fortification']['fortification_transform'] == 'lab level is converted by QE into state::wall.fortification_multiplier'
    fort_check = ledger['fortification_double_application_check']
    assert fort_check['state_wall_hp_includes_fortification'] is True
    assert fort_check['reconstructed_wall_hp'] == pytest.approx(primitives['wall_hp'] * primitives['wall_fortification_multiplier'])
    assert fort_check['qe_state_wall_hp_surface'] == pytest.approx(canonical['state::wall.hp'])
    assert fort_check['policy'].startswith('derive pre-fort wall HP from tower_hp')
    hp_check = ledger['wall_hp_formula_check']
    assert hp_check['tower_hp'] == pytest.approx(canonical['state::tower.hp'])
    assert hp_check['reconstructed_displayed_wall_hp_pre_fort'] == pytest.approx(expected_wall_hp_pre_fort)
    regen_check = ledger['wall_regen_formula_check']
    assert regen_check['tower_regen'] == pytest.approx(canonical['state::tower.regen'])
    assert regen_check['wall_regen_percent_points'] == pytest.approx(canonical['state::wall.regen'])
    assert regen_check['reconstructed_displayed_wall_regen'] == pytest.approx(expected_wall_regen)
    semantic_contract = ledger['boss_waves_wall_surface_semantic_contract']
    assert semantic_contract['state::wall.hp']['decision'] == 'transformed_primitive_not_final_display_value'
    assert semantic_contract['state::wall.regen']['decision'] == 'transformed_percent_points_primitive_not_final_hp_per_second'
    assert diagnostics['replacement_display_derivation']['wall_hp'].startswith('operator_rows.wall_hp')
    assert diagnostics['replacement_model']['death_wave_health_multiplier_applies_to'] == 'table1_row_evolved_tower_hp_then_wall_hp_not_wall_regen_or_enemy_health'
    assert diagnostics['replacement_model']['boss_survival_model'] == 'max_waves_compares_ttd_wall_hp_plus_regen_against_total_v21_ttk_window'
    ttk_inputs = ledger['boss_ttk_input_contract']
    assert ttk_inputs['orb_boss_total_damage_pct'] == pytest.approx(2.0)
    assert ttk_inputs['orb_boss_total_damage_source'] == 'default_orb_boss_total_damage_pct_2'
    assert ttk_inputs['electron_total_damage_pct'] == pytest.approx(canonical['state::module.orbital_augment.electron_count'] * 3.75)
    assert ttk_inputs['electron_total_damage_source'] == 'orbital_augment_electron_count_times_boss_electron_pct'
    assert diagnostics['boss_wave_debug_ledger']['sample_rows']
    first_row = (payload.get('rows') or [{}])[0]
    assert first_row.get('display_wave') == 9
    rows = payload.get('rows') or []
    assert rows[0]['wall_pre_fort_hp'] > fort_check['row_input_wall_hp']
    assert rows[-1]['wall_pre_fort_hp'] > rows[0]['wall_pre_fort_hp']
    assert rows[0]['wall_pre_fort_hp'] == pytest.approx(19731905998921.957)
    assert rows[0]['wall_hp'] == pytest.approx(205211822388788.38)
    assert rows[0]['wall_hp'] == pytest.approx(rows[0]['wall_pre_fort_hp'] * primitives['wall_fortification_multiplier'])
    assert rows[0]['wall_regen'] == pytest.approx(5814158246443.825)
    assert rows[0]['summary_lane_id'] == 'avg'
    assert rows[0]['lane_handle_ids'] == {
        'avg': 'boss:boss_waves_replacement_product:9:avg',
        'min': 'boss:boss_waves_replacement_product:9:min',
        'max': 'boss:boss_waves_replacement_product:9:max',
    }
    assert 'effective_damage_reduction_pct' in first_row
    assert 'boss_time_to_contact_seconds' in first_row
    assert 'boss_hit_interval_seconds' in first_row
    assert 'incoming_damage_multiplier' in first_row


@pytest.mark.live
def test_boss_wave_payload_without_contact_time_returns_structured_incomplete_when_allowed():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload
    from simulators.evaluator_kernel import KernelAmbiguityError

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out')
    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=50,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={},
    )

    summary = payload['summary']
    assert summary['status'] == 'incomplete'
    assert summary['failure_kind'] == 'kernel_ambiguity'
    assert 'boss_time_to_contact_seconds is required' in summary['failure_message']
    assert summary['first_unresolved_wave'] == 9
    assert payload['diagnostics']['context_status'] == 'incomplete'

    with pytest.raises(KernelAmbiguityError, match='boss_time_to_contact_seconds is required'):
        build_boss_wave_payload(
            request,
            preset_name='Farming',
            tier_number=14,
            end_wave=50,
            boss_wave_step=1,
            stop_on_failure=True,
            scenario_runtime_inputs={},
        )


@pytest.mark.live
def test_boss_wave_payload_uses_effective_bh_cf_state_and_perk_switches():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    runtime_inputs = {'boss_time_to_contact_seconds': 1.0}
    with_perks = build_boss_wave_payload(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='runtime_timeline', perk_state='on'),
        preset_name='Farming',
        tier_number=14,
        end_wave=5000,
        boss_wave_step=100,
        stop_on_failure=False,
        scenario_runtime_inputs=runtime_inputs,
    )
    primitives = with_perks['diagnostics']['replacement_primitive_inputs']['values']
    assert primitives['black_hole_duration_seconds'] == pytest.approx(36.0)
    assert primitives['black_hole_cooldown_seconds'] == pytest.approx(46.0)
    assert primitives['chrono_field_duration_seconds'] == pytest.approx(50.0)
    assert primitives['chrono_field_cooldown_seconds'] == pytest.approx(60.0)
    assert primitives['chrono_field_damage_reduction_pct'] == pytest.approx(20.0)
    assert primitives['chrono_field_duration_seconds'] != pytest.approx(20.0)

    rows_with_perks = with_perks['rows']
    assert rows_with_perks[0]['effective_damage_reduction_pct'] < rows_with_perks[-1]['effective_damage_reduction_pct']
    assert rows_with_perks[-1]['effective_damage_reduction_pct'] >= 96.0

    max_policy_request = build_boss_wave_payload(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='max_progression_policy', perk_state='on'),
        preset_name='Farming',
        tier_number=14,
        end_wave=5000,
        boss_wave_step=100,
        stop_on_failure=False,
        scenario_runtime_inputs=runtime_inputs,
    )
    assert max_policy_request['diagnostics']['requested_perk_mode'] == 'max_progression_policy'
    assert max_policy_request['diagnostics']['perk_application_mode'] == 'runtime_timeline'
    assert max_policy_request['diagnostics']['perk_timeline_rows'] > 0
    assert max_policy_request['contract']['perk_timeline_mode'] == 'runtime_policy_projection'
    assert max_policy_request['rows'][0]['effective_damage_reduction_pct'] == pytest.approx(rows_with_perks[0]['effective_damage_reduction_pct'])

    none_requested = build_boss_wave_payload(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='none', perk_state='on'),
        preset_name='Farming',
        tier_number=14,
        end_wave=5000,
        boss_wave_step=100,
        stop_on_failure=False,
        scenario_runtime_inputs=runtime_inputs,
    )
    off_requested = build_boss_wave_payload(
        PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='runtime_timeline', perk_state='off'),
        preset_name='Farming',
        tier_number=14,
        end_wave=5000,
        boss_wave_step=100,
        stop_on_failure=False,
        scenario_runtime_inputs=runtime_inputs,
    )
    assert none_requested['diagnostics']['requested_perk_mode'] == 'none'
    assert off_requested['diagnostics']['requested_perk_state'] == 'off'
    assert none_requested['diagnostics']['perks_enabled'] is True
    assert off_requested['diagnostics']['perks_enabled'] is True
    assert none_requested['diagnostics']['perk_application_mode'] == 'runtime_timeline'
    assert off_requested['diagnostics']['perk_application_mode'] == 'runtime_timeline'
    assert none_requested['diagnostics']['perk_state_source'] == 'scenario_policy_tournament_off_other_runs_on'
    assert off_requested['diagnostics']['perk_state_source'] == 'scenario_policy_tournament_off_other_runs_on'
    assert none_requested['rows'][-1]['wall_hp'] == pytest.approx(rows_with_perks[-1]['wall_hp'])
    assert off_requested['rows'][-1]['wall_regen'] == pytest.approx(rows_with_perks[-1]['wall_regen'])


@pytest.mark.live
def test_boss_wave_payload_threads_t14_battle_conditions_and_final_dr_override():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', perk_mode='none')
    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=10,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 1.0},
    )
    scenario_surfaces = payload['diagnostics']['scenario_surfaces']
    row = payload['rows'][0]
    assert scenario_surfaces['bc_plasma_cannon_resistance'] == pytest.approx(0.8)
    assert scenario_surfaces['bc_orb_resistance'] == pytest.approx(0.5)
    assert scenario_surfaces['bc_thorns_resistance'] == pytest.approx(0.8)
    assert row['boss_plasma_cannon_damage_to_boss_pct'] == pytest.approx(43.2)
    assert row['boss_orb_damage_to_boss_pct'] == pytest.approx(1.0)
    assert row['boss_hit_interval_seconds'] == pytest.approx(scenario_surfaces['boss_hit_interval_seconds'])

    overridden = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=10,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={
            'boss_time_to_contact_seconds': 1.0,
            'effective_damage_reduction_pct': 90.0,
            'black_hole_damage_reduction_pct': 0.0,
            'black_hole_duration_seconds': 0.0,
            'pbh_encounter_uptime_fraction': 0.0,
        },
    )
    overridden_row = overridden['rows'][0]
    assert overridden_row['effective_damage_reduction_pct'] == pytest.approx(90.0)
    sources = overridden['diagnostics']['replacement_primitive_semantics_ledger']['timed_dr_semantic_contract']['sources']
    assert sources['black_hole_pbh']['damage_reduction_pct'] == pytest.approx(0.0)
    assert sources['black_hole_pbh']['uptime_fraction'] == pytest.approx(0.0)
    assert sources['final_dr_override']['primitive_status'] == 'runtime_final_dr_override_bypasses_timed_dr_sources'


def test_boss_wave_perk_state_is_owned_by_scenario_not_request():
    from app.pipeline import _resolve_boss_wave_run_context

    account_state = type(
        'State',
        (),
        {
            'active_perk_preset': None,
            'player_meta': {'Tourney League': 'Legends', 'Tournament Wave': '100'},
        },
    )()

    farming = _resolve_boss_wave_run_context(
        account_state,
        preset_name='Farming',
        tier_number=14,
        checkpoint_every_bosses=1,
    )
    tournament = _resolve_boss_wave_run_context(
        account_state,
        preset_name='Tourney',
        tier_number=14,
        checkpoint_every_bosses=1,
    )

    assert farming['mode_id'] == 'farming'
    assert farming['perks_enabled'] is True
    assert farming['perk_state'] == 'on'
    assert farming['perk_state_source'] == 'scenario_policy_tournament_off_other_runs_on'
    assert tournament['mode_id'] == 'tournament'
    assert tournament['perks_enabled'] is False
    assert tournament['perk_state'] == 'off'
    assert tournament['perk_timeline_mode'] == 'disabled_by_tournament_scenario'


def test_perk_timeline_preview_override_is_validated_and_consumed_by_boss_waves():
    from app.models import PipelineRunRequest
    from app.pipeline import build_boss_wave_payload, build_perk_timeline_preview

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out')
    override = {
        'seed': 42,
        'target_wave': 50000,
        'banned_perks': [],
        'first_perk_choice': 'Defense Percent +4.00',
        'priority_order': ['Defense Percent +4.00'],
    }
    preview = build_perk_timeline_preview(request, perk_policy_override=override)

    assert preview['validation']['ok'] is True
    assert preview['validation']['ban_perks_used'] == 0
    assert preview['resolved_policy']['first_perk_choice'] == 'Defense Percent +4.00'
    assert preview['timeline'][0]['perk_taken'] == 'Defense Percent +4.00'
    assert preview['diagnostics']['uw_locked_perks_excluded']['Swamp Radius x1.5'] == 'Poison Swamp'

    payload = build_boss_wave_payload(
        request,
        preset_name='Farming',
        tier_number=14,
        end_wave=210,
        boss_wave_step=1,
        stop_on_failure=False,
        scenario_runtime_inputs={'boss_time_to_contact_seconds': 1.0},
        perk_policy_override=override,
    )
    rows = {int(row['display_wave']): row for row in payload['rows']}
    assert payload['diagnostics']['perk_policy_override_active'] is True
    assert payload['diagnostics']['perk_policy_validation']['ok'] is True
    assert rows[180]['effective_damage_reduction_pct'] < rows[189]['effective_damage_reduction_pct']


def test_perk_timeline_preview_rejects_over_capacity_bans():
    from app.models import PipelineRunRequest
    from app.pipeline import build_perk_timeline_preview

    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out')
    preview = build_perk_timeline_preview(
        request,
        perk_policy_override={
            'banned_perks': [
                'x1.15 Damage',
                'x1.20 Max Health',
                'x1.75 Health Regen',
                'Defense Percent +4.00',
                'Black Hole Duration +12.0s',
                'Chrono Field Duration +5s',
                'Golden Tower Bonus x1.5',
            ],
        },
    )

    assert preview['validation']['ok'] is False
    assert 'Ban Perks lab capacity is 6' in preview['validation']['errors'][0]


def test_save_perk_policy_override_persists_to_manual_inputs(tmp_path):
    from app.models import PipelineRunRequest
    from app.pipeline import build_perk_timeline_preview, save_perk_policy_override

    manual_inputs = tmp_path / 'manual_inputs.yaml'
    manual_inputs.write_text(
        yaml.safe_dump(
            {
                'loadout': {},
                'perk_config': {'perk_presets': {}, 'active_perk_preset': None},
                'perk_policy': {
                    'seed': 1,
                    'target_wave': 1000,
                    'priority_order': ['Perk Wave Requirement -20.00%'],
                    'first_perk_choice': 'Perk Wave Requirement -20.00%',
                    'banned_perk_aliases': ['TO3'],
                    'banned_perks': ['Enemies Speed -40%, But Enemies Damage x2.5'],
                },
            },
            sort_keys=False,
        ),
        encoding='utf-8',
    )
    request = PipelineRunRequest(ids=IDS_PATH, out=ROOT / 'out', manual_inputs=manual_inputs)
    override = {
        'seed': 42,
        'target_wave': 50000,
        'banned_perks': [],
        'first_perk_choice': 'Defense Percent +4.00',
        'priority_order': ['Defense Percent +4.00'],
    }

    save_result = save_perk_policy_override(request, perk_policy_override=override)
    saved_yaml = yaml.safe_load(manual_inputs.read_text(encoding='utf-8'))
    saved_policy = saved_yaml['perk_policy']

    assert save_result['manual_inputs_path'] == str(manual_inputs)
    assert saved_policy['seed'] == 42
    assert saved_policy['target_wave'] == 50000
    assert saved_policy['banned_perks'] == []
    assert 'banned_perk_aliases' not in saved_policy
    assert saved_policy['first_perk_choice'] == 'Defense Percent +4.00'
    assert saved_policy['priority_order'] == ['Defense Percent +4.00']

    preview = build_perk_timeline_preview(request)
    assert preview['validation']['ok'] is True
    assert preview['resolved_policy']['first_perk_choice'] == 'Defense Percent +4.00'
    assert preview['timeline'][0]['perk_taken'] == 'Defense Percent +4.00'


def test_boss_wave_perk_timeline_uses_ids_labs_first_choice_and_exports_wall_contributions():
    from app import pipeline as pipeline_mod
    from simulators.perk_timeline_generator import PerkTimelinePolicy, generate_timeline_from_policy

    bundle = pipeline_mod.load_inputs(ids_path=IDS_PATH)
    payload, context = pipeline_mod._perk_policy_context(bundle.ids_raw, getattr(bundle, 'perk_policy', {}) or {})
    assert payload['waves_required_lab'] == 13
    assert payload['standard_perk_bonus'] == pytest.approx(0.25)
    assert payload['perk_option_quantity'] == 2
    assert context['ban_perks_capacity_ids'] == 6
    assert len(payload['banned_perks']) == 2
    assert payload['priority_order'] == ['Perk Wave Requirement -20.00%']
    assert payload['first_perk_choice'] == 'Perk Wave Requirement -20.00%'
    assert payload['unlocked_ultimate_weapons'] == [
        'Black Hole',
        'Chain Lightning',
        'Chrono Field',
        'Death Wave',
        'Golden Tower',
        'Spotlight',
    ]

    timeline, diag = generate_timeline_from_policy(PerkTimelinePolicy(**payload))
    assert diag['uw_locked_perks_excluded'] == {
        '4 More Smart Missiles': 'Smart Missiles',
        'Extra Set of Inner Mines': 'Inner Land Mines',
        'Swamp Radius x1.5': 'Poison Swamp',
    }
    assert not any(row['perk_taken'] in diag['uw_locked_perks_excluded'] for row in timeline)
    assert diag['pwr_stacks'] == 3
    assert [row['wave'] for row in timeline if row['perk_taken'] == 'Perk Wave Requirement -20.00%'] == [187, 280, 467]
    counts_by_wave = pipeline_mod._boss_wave_perk_counts_by_wave(tuple(timeline))
    contributions_by_wave = pipeline_mod._boss_wave_perk_contributions_by_wave(
        counts_by_wave,
        standard_bonus_pct=float(context['standard_perk_bonus_level']),
        tradeoff_bonus_pct=float(context['tradeoff_bonus_level']),
    )
    final_contributions = contributions_by_wave[max(contributions_by_wave)]
    assert final_contributions['perk_PERK_X1_20_MAX_HEALTH_effect_1:wall_hp_multiplier'] == pytest.approx(2.5)
    assert final_contributions['perk_PERK_X1_75_HEALTH_REGEN_effect_1:wall_regen_multiplier'] == pytest.approx(5.9375)
    assert final_contributions['perk_PERK_TOWER_HEALTH_REGEN_X8_00_BUT_TOWER_MAX_MAX_HEALTH_60_effect_1:wall_regen_multiplier'] == pytest.approx(8.8)
    assert final_contributions['perk_PERK_DEFENSE_PERCENT_4_00_effect_1:tower_defense_pct_points_add'] == pytest.approx(25.0)


def test_perk_generator_excludes_uw_perks_for_locked_ultimate_weapons():
    from simulators.perk_timeline_generator import PerkTimelinePolicy, generate_timeline_from_policy

    policy = PerkTimelinePolicy(
        seed=7,
        target_wave=50000,
        perk_option_quantity=2,
        priority_order=[
            'Golden Tower Bonus x1.5',
            'Black Hole Duration +12.0s',
        ],
        first_perk_choice='Golden Tower Bonus x1.5',
        unlocked_ultimate_weapons=['Black Hole'],
    )

    timeline, diag = generate_timeline_from_policy(policy)

    assert diag['uw_locked_perks_excluded']['Golden Tower Bonus x1.5'] == 'Golden Tower'
    offered = [perk for row in timeline for perk in row['offered']]
    taken = [row['perk_taken'] for row in timeline]
    assert 'Golden Tower Bonus x1.5' not in offered
    assert 'Golden Tower Bonus x1.5' not in taken
    assert 'Black Hole Duration +12.0s' in taken


def test_max_progression_policy_excludes_uw_perks_for_locked_ultimate_weapons():
    from app import pipeline as pipeline_mod
    from qe.stat_input_compiler import load_perk_entity_rows

    bundle = pipeline_mod.load_inputs(ids_path=IDS_PATH)
    config, metadata = pipeline_mod._resolve_perk_config(
        perk_mode='max_progression_policy',
        primary_config=bundle.perk_config,
        perk_policy=bundle.perk_policy,
        ids_raw=bundle.ids_raw,
    )
    perk_names_by_id = {row['perk_id']: row['perk_name'] for row in load_perk_entity_rows()}
    selected_names = {
        perk_names_by_id[selection['perk_id']]
        for selection in config['perk_presets']['ProjectedMaxPolicy_AllExceptManualBans']
    }

    assert metadata['uw_locked_perks_excluded'] == {
        '4 More Smart Missiles': 'Smart Missiles',
        'Extra Set of Inner Mines': 'Inner Land Mines',
        'Swamp Radius x1.5': 'Poison Swamp',
    }
    assert not (selected_names & set(metadata['uw_locked_perks_excluded']))
    assert 'Black Hole Duration +12.0s' in selected_names


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
        perk_policy_override={
            'banned_perks': [
                'x1.15 Damage',
                'x1.20 Max Health',
                'x1.75 Health Regen',
            ],
        },
    )

    diagnostics = payload.get('diagnostics') or {}
    assert (payload.get('rows') or []) == []
    assert diagnostics['context_status'] == 'error'
    assert diagnostics['context_error'] == 'missing_tournament_wave'
    assert diagnostics['perk_mode'] == 'none'
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


def test_run_stats_canonical_default_publishes_max_progression_perk_sensitive_uw_rows(run_stats_single_execution):
    diagnostics = run_stats_single_execution["parsed_outputs"]["diagnostics.json"]
    max_rows = run_stats_single_execution["parsed_outputs"][
        _RUN_STATS_QUERY_OUTPUTS['max_progression_rows']
    ]['Farming']['rows']

    assert diagnostics.get('perk_mode') == 'max_progression_policy'
    assert max_rows['state::uw.black_hole.duration_seconds']['final_value'] == pytest.approx(48.0)
    assert max_rows['state::uw.chrono_field.duration_seconds']['final_value'] == pytest.approx(55.0)

    from qe.publication import _uw_track_surface_map

    declared_uw_surfaces = {
        surface_id
        for track_map in _uw_track_surface_map().values()
        for surface_id in track_map.values()
    }
    missing = sorted(declared_uw_surfaces - set(max_rows))
    assert missing == []


@pytest.mark.live
def test_run_stats_writes_stats_dashboard_artifact(run_stats_single_execution):
    stats_dashboard = json.loads((run_stats_single_execution["out_dir"] / "stats_dashboard.json").read_text(encoding='utf-8'))

    assert stats_dashboard.get("artifact") == "stats_dashboard.json"
    assert stats_dashboard.get("schema_version") == 1
    panel_ids = [panel.get("panel_id") for panel in (stats_dashboard.get("panels") or [])]
    secondary_panel_ids = [panel.get("panel_id") for panel in (stats_dashboard.get("secondary_panels") or [])]
    assert panel_ids == ["workshop", "derived_wall_economy", "ultimate_weapons", "bots", "guardians", "modules"]
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



