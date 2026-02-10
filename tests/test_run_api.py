from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.api import (
    TASK_BASE_STATS,
    TASK_STAT_INPUTS,
    TASK_EHP_SLICE,
    TASK_INVENTORY,
    TASK_LOADOUT,
    TASK_MAX_WAVE,
    run_task,
)
from tower_sim.run.spec_loader import load_problem_spec, spec_as_dict


def _fixture_ids_snapshot():
    return compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )


def test_run_task_base_stats() -> None:
    ids_snapshot = _fixture_ids_snapshot()
    result = run_task(TASK_BASE_STATS, ids_snapshot=ids_snapshot)
    assert result["ok"] is True
    assert result["result"]["statbook"]


def test_run_task_inventory() -> None:
    ids_snapshot = _fixture_ids_snapshot()
    result = run_task(TASK_INVENTORY, ids_snapshot=ids_snapshot)
    assert result["ok"] is True
    assert "workshop" in result["result"]


def test_run_task_stat_inputs() -> None:
    ids_snapshot = _fixture_ids_snapshot()
    result = run_task(TASK_STAT_INPUTS, ids_snapshot=ids_snapshot)
    assert result["ok"] is True
    assert "stat_inputs" in result["result"]


def test_run_task_loadout() -> None:
    ids_snapshot = _fixture_ids_snapshot()
    result = run_task(TASK_LOADOUT, ids_snapshot=ids_snapshot)
    assert result["ok"] is True
    assert "cards" in result["result"]
    modules = result["result"]["modules"]
    assert "Armor" in modules
    assert modules["Armor"]["allocation"]["primary_level"] is not None
    assert modules["Armor"]["allocation"]["assist_level"] is not None


def test_run_task_ehp_slice() -> None:
    ids_snapshot = _fixture_ids_snapshot()
    result = run_task(
        TASK_EHP_SLICE,
        {"enabled_stats": ["tower_hp"], "allow_out_of_scope": True},
        ids_snapshot=ids_snapshot,
    )
    assert result["ok"] is True
    assert result["result"]["stats"]


def test_run_task_max_wave() -> None:
    ids_snapshot = _fixture_ids_snapshot()
    spec_path = Path("tests/fixtures/specs/sample_spec.yaml")
    spec = load_problem_spec(spec_path)
    result = run_task(
        TASK_MAX_WAVE,
        {"problem_spec": spec_as_dict(spec)},
        ids_snapshot=ids_snapshot,
    )
    assert result["task"] == TASK_MAX_WAVE
    assert "w_max" in result["result"]
    assert "assumptions_manifest" in result["result"]


def test_run_task_rejects_unknown_args() -> None:
    ids_snapshot = _fixture_ids_snapshot()
    with pytest.raises(ValueError):
        run_task(TASK_BASE_STATS, {"extra": "no"}, ids_snapshot=ids_snapshot)
