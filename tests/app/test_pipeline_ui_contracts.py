from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


def test_request_adapter_and_execute_pipeline_emit_trace(tmp_path):
    from app.pipeline import PipelineRunRequest, execute_pipeline, get_default_run_stats_session

    get_default_run_stats_session.cache_clear()
    request = PipelineRunRequest(
        ids=ROOT / 'input' / 'imports' / 'ids.csv',
        out=tmp_path / 'out',
        preset='Farming',
        state_mode='max_progression',
        manual_inputs=None,
        perk_mode='max_progression_policy',
        include_slow_audits=False,
        perk_state='auto',
    )
    result = execute_pipeline(request)

    assert result.exit_code == 0
    assert (result.out_dir / 'pipeline_trace.json').exists()
    trace = result.pipeline_trace.to_dict()
    assert trace['execution_path']['recompute_mode'] is not None
    assert 'cache_status' in trace['execution_path']
    assert 'runtime_consumers' in trace['execution_path']
    stage_ids = [stage['stage_id'] for stage in trace['stages']]
    assert stage_ids[:4] == ['input_load', 'runtime_account_assembly', 'compare_materialization', 'stat_resolution']
    assert 'artifact_write' in stage_ids


def test_trace_stage_cache_status_markers_for_miss_then_hit(tmp_path):
    from app.pipeline import (
        PipelineRunRequest,
        _build_pipeline_trace_from_artifacts,
        get_default_run_stats_session,
    )

    get_default_run_stats_session.cache_clear()
    session = get_default_run_stats_session()
    request = PipelineRunRequest(
        ids=ROOT / 'input' / 'imports' / 'ids.csv',
        out=tmp_path / 'out',
    )
    args = type('PipelineArgs', (), {})()
    args.ids = request.ids
    args.out = request.out
    args.preset = request.preset
    args.state_mode = request.state_mode
    args.manual_inputs = request.manual_inputs
    args.perk_mode = request.perk_mode
    args.include_slow_audits = request.include_slow_audits
    args.perk_state = request.perk_state

    first_artifacts = session.build_run_stats_artifacts(args)
    second_artifacts = session.build_run_stats_artifacts(args)
    first_trace = _build_pipeline_trace_from_artifacts(
        request=request,
        total_elapsed_ms=0.0,
        diagnostics=first_artifacts['diagnostics'],
    ).to_dict()
    second_trace = _build_pipeline_trace_from_artifacts(
        request=request,
        total_elapsed_ms=0.0,
        diagnostics=second_artifacts['diagnostics'],
    ).to_dict()

    first_stages = {stage['stage_id']: stage for stage in first_trace['stages']}
    second_stages = {stage['stage_id']: stage for stage in second_trace['stages']}

    assert first_trace['execution_path']['cache_status'] == 'cold'
    assert first_stages['input_load']['status'] == 'executed'
    assert first_stages['runtime_account_assembly']['status'] == 'executed'
    assert first_stages['input_load']['outputs_summary']['status'] == 'executed'
    assert first_stages['runtime_account_assembly']['outputs_summary']['status'] == 'executed'

    assert second_trace['execution_path']['cache_status'] == 'warm'
    assert second_stages['input_load']['status'] == 'cache_hit'
    assert second_stages['runtime_account_assembly']['status'] == 'cache_hit'
    assert second_stages['input_load']['outputs_summary']['status'] == 'cache_hit'
    assert second_stages['runtime_account_assembly']['outputs_summary']['status'] == 'cache_hit'
    assert second_stages['input_load']['elapsed_ms'] == 0.0
    assert second_stages['runtime_account_assembly']['elapsed_ms'] == 0.0


def test_trace_artifact_is_listed_in_generated_files(tmp_path):
    from app.pipeline import PipelineRunRequest, execute_pipeline

    result = execute_pipeline(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=tmp_path / 'out',
        )
    )
    generated = {path.name for path in result.generated_files}
    assert 'pipeline_trace.json' in generated


def test_build_verification_snapshot_set_runs_default_matrix(tmp_path):
    from app.pipeline import PipelineRunRequest, build_verification_snapshot_set

    results = build_verification_snapshot_set(
        PipelineRunRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            out=tmp_path / 'matrix',
        )
    )
    assert len(results) == 4
    labels = {(result.request.preset, result.request.state_mode) for result in results}
    assert ('Farming', 'start_of_run') in labels
    assert ('Farming', 'max_progression') in labels
    assert ('Tourney', 'start_of_run') in labels
    assert ('Tourney', 'max_progression') in labels


def test_resolve_fast_checkpoint_returns_requested_surfaces():
    from app.pipeline import FastCheckpointRequest, resolve_fast_checkpoint

    result = resolve_fast_checkpoint(
        FastCheckpointRequest(
            ids=ROOT / 'input' / 'imports' / 'ids.csv',
            preset='Farming',
            state_mode='start_of_run',
            requested_surface_ids=('state::tower.hp', 'state::wall.hp'),
        )
    )

    rows = result.statbook.get('rows') or {}
    assert result.diagnostics['resolver_kind'] == 'simulator_checkpoint_qe_light'
    assert set(rows) == {'state::tower.hp', 'state::wall.hp'}
