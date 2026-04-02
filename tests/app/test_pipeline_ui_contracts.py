from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


def test_request_adapter_and_execute_pipeline_emit_trace(tmp_path):
    from app.pipeline import PipelineRunRequest, execute_pipeline

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
    input_load_stage = next(stage for stage in trace['stages'] if stage['stage_id'] == 'input_load')
    assert input_load_stage['outputs_summary']['manual_inputs_path'] == 'input/manual_inputs.yaml'


@pytest.mark.live
def test_trace_input_load_manual_inputs_path_respects_override(tmp_path):
    from app.pipeline import PipelineRunRequest, execute_pipeline

    request = PipelineRunRequest(
        ids=ROOT / 'input' / 'imports' / 'ids.csv',
        out=tmp_path / 'out',
        manual_inputs=ROOT / 'tests' / '_fixtures' / 'manual_inputs.partial.yaml',
    )
    result = execute_pipeline(request)

    assert result.exit_code == 0
    trace = result.pipeline_trace.to_dict()
    input_load_stage = next(stage for stage in trace['stages'] if stage['stage_id'] == 'input_load')
    assert input_load_stage['outputs_summary']['manual_inputs_path'] == 'tests/_fixtures/manual_inputs.partial.yaml'


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
