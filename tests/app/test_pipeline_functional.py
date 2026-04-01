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
    _RUN_STATS_QUERY_OUTPUTS,
    _path_cache_token,
    _effective_manual_inputs_path,
)
from app.pipeline import RunStatsSession
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
IDS_PATH = ROOT / "input" / "imports" / "ids.csv"


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
def test_diagnostics_depth(tmp_path):
    """diagnostics.json must contain real populated content, not empty placeholders."""
    out_dir = tmp_path / "out"
    request = PipelineRunRequest(ids=IDS_PATH, out=out_dir, preset='Farming', state_mode='start_of_run')
    execute_pipeline(request)

    diag = json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8'))

    assert diag.get('stat_input_count', 0) > 0, "stat_input_count must be non-zero"
    assert diag.get('statbook_row_count', 0) > 0, "statbook_row_count must be non-zero"
    assert 'state_matrix' in diag and diag['state_matrix'], "state_matrix must be populated"
    assert 'start_of_run' in diag['state_matrix'] and 'max_progression' in diag['state_matrix']
    assert diag['state_matrix']['start_of_run'].get('input_count', 0) > 0
    assert 'kb_incomplete_areas' in diag
    assert 'audits' in diag
    assert 'ep_compare_summary' in diag


@pytest.mark.live
def test_publishable_statbook_populated(tmp_path):
    """statbook_publishable.json must be non-empty and structurally valid."""
    out_dir = tmp_path / "out"
    request = PipelineRunRequest(ids=IDS_PATH, out=out_dir, preset='Farming', state_mode='start_of_run')
    execute_pipeline(request)

    pub = json.loads((out_dir / 'statbook_publishable.json').read_text(encoding='utf-8'))
    assert 'rows' in pub and len(pub['rows']) > 0, "statbook_publishable.json rows must be non-empty"


@pytest.mark.live
def test_optimizer_scores_populated(tmp_path):
    """optimizer_scores.json must be non-empty."""
    out_dir = tmp_path / "out"
    request = PipelineRunRequest(ids=IDS_PATH, out=out_dir, preset='Farming', state_mode='start_of_run')
    execute_pipeline(request)

    scores = json.loads((out_dir / 'optimizer_scores.json').read_text(encoding='utf-8'))
    assert isinstance(scores, dict) and len(scores) > 0, "optimizer_scores.json must be non-empty"


@pytest.mark.live
def test_run_stats_canonical_output_filenames(tmp_path):
    """RunStatsSession.execute() must write canonical run_stats_query_plan_* and run_stats_query_rows_* filenames."""
    out_dir = tmp_path / "run_stats_out"
    out_dir.mkdir()
    args = SimpleNamespace(
        ids=IDS_PATH, out=out_dir, perk_mode='none', perk_state='auto', manual_inputs=None,
    )
    session = RunStatsSession()
    rc = session.execute(args)
    assert rc == 0

    for key, filename in _RUN_STATS_QUERY_OUTPUTS.items():
        assert (out_dir / filename).exists(), f"Expected canonical output {filename} but it was not written"

    legacy_filenames = [
        'stat_inputs_start_of_run.json', 'stat_inputs_max_progression.json',
        'statbook_start_of_run.json', 'statbook_max_progression.json',
    ]
    for name in legacy_filenames:
        assert not (out_dir / name).exists(), f"Legacy output {name} must not be written"


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
def test_run_stats_diagnostics_contains_write_outputs_ms(tmp_path):
    """diagnostics.json persisted by RunStatsSession.execute() must include write_outputs_ms."""
    out_dir = tmp_path / "run_stats_out"
    out_dir.mkdir()
    args = SimpleNamespace(
        ids=IDS_PATH, out=out_dir, perk_mode='none', perk_state='auto', manual_inputs=None,
    )
    session = RunStatsSession()
    rc = session.execute(args)
    assert rc == 0

    diag = json.loads((out_dir / 'diagnostics.json').read_text(encoding='utf-8'))
    timings = diag.get('timings_ms', {})
    assert 'write_outputs_ms' in timings, "diagnostics.json must contain write_outputs_ms from final write"
    assert isinstance(timings['write_outputs_ms'], (int, float)), "write_outputs_ms must be numeric"


@pytest.mark.live
def test_ep_oracle_compare_populated(tmp_path):
    """ep_oracle_compare.json must be a non-empty dict."""
    out_dir = tmp_path / "out"
    request = PipelineRunRequest(ids=IDS_PATH, out=out_dir, preset='Farming', state_mode='start_of_run')
    execute_pipeline(request)

    compare = json.loads((out_dir / 'ep_oracle_compare.json').read_text(encoding='utf-8'))
    assert isinstance(compare, dict) and len(compare) > 0
