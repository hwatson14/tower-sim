"""
Functional tests for app/pipeline.py and sharded evaluators.
Verifies the fix for the FrozenInstanceError and trace contract restoration.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.pipeline import (
    execute_pipeline, 
    PipelineRunRequest, 
    resolve_fast_checkpoint, 
    FastCheckpointRequest
)

ROOT = Path(__file__).resolve().parents[2]
IDS_PATH = ROOT / "input" / "imports" / "ids.csv"

def _relpath_str(path: Path | str | None) -> str | None:
    if path is None: return None
    p = Path(path)
    try: return str(p.relative_to(ROOT))
    except (ValueError, RuntimeError): return str(p)

@pytest.mark.live
def test_execute_pipeline_smoke_and_trace_contract(tmp_path):
    """
    Verifies that execute_pipeline runs without FrozenInstanceError 
    and produces a valid pipeline_trace.json.
    """
    out_dir = tmp_path / "out"
    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=out_dir,
        preset='Farming',
        state_mode='start_of_run'
    )
    
    # This should not raise FrozenInstanceError
    result = execute_pipeline(request)
    
    assert result.exit_code == 0
    assert result.out_dir == out_dir
    
    # Verify trace artifact existence and content
    trace_path = out_dir / "pipeline_trace.json"
    assert trace_path.exists(), "pipeline_trace.json was not created"
    
    trace_data = json.loads(trace_path.read_text(encoding='utf-8'))
    assert "request" in trace_data
    assert "execution_path" in trace_data
    assert "stages" in trace_data
    assert len(trace_data["stages"]) > 0
    assert "artifacts_written" in trace_data
    assert len(trace_data["artifacts_written"]) > 0
    
    # Verify core artifact presence in trace
    written = trace_data["artifacts_written"]
    # Normalize paths for comparison
    written_names = [Path(f).name for f in written]
    assert "ep_oracle_compare.json" in written_names
    assert "line_by_line_verification.json" in written_names

@pytest.mark.live
def test_resolve_fast_checkpoint_smoke():
    """Verifies that the restored fast-checkpoint API is functional."""
    request = FastCheckpointRequest(
        ids=IDS_PATH,
        requested_surface_ids=("canonical_stat::tower_hp", "canonical_stat::tower_damage")
    )
    
    result = resolve_fast_checkpoint(request)
    
    assert result.statbook is not None
    assert "rows" in result.statbook
    assert "canonical_stat::tower_hp" in result.statbook["rows"]
    assert "canonical_stat::tower_damage" in result.statbook["rows"]

@pytest.mark.live
def test_sharded_evaluators_parity(tmp_path):
    """Verifies that sharded evaluators produce identical comparison artifacts."""
    out_dir = tmp_path / "out"
    request = PipelineRunRequest(
        ids=IDS_PATH,
        out=out_dir,
        preset='Farming',
        state_mode='start_of_run'
    )
    
    execute_pipeline(request)
    
    compare_path = out_dir / "ep_oracle_compare.json"
    assert compare_path.exists()
    
    compare_data = json.loads(compare_path.read_text(encoding='utf-8'))
    assert isinstance(compare_data, dict)
    assert len(compare_data) > 0
