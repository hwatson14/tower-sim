from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.api import (
    TASK_BASE_STATS,
    TASK_EHP_SLICE,
    TASK_INVENTORY,
    TASK_LOADOUT,
    TASK_MAX_WAVE,
    run_task,
)
from tower_sim.run.spec_loader import load_problem_spec, spec_as_dict


def _fixture_ids_state():
    return parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))


def test_run_task_base_stats() -> None:
    ids_state = _fixture_ids_state()
    result = run_task(TASK_BASE_STATS, ids_state=ids_state)
    assert result["ok"] is True
    assert result["result"]["statbook"]


def test_run_task_inventory() -> None:
    ids_state = _fixture_ids_state()
    result = run_task(TASK_INVENTORY, ids_state=ids_state)
    assert result["ok"] is True
    assert "workshop" in result["result"]


def test_run_task_loadout() -> None:
    ids_state = _fixture_ids_state()
    result = run_task(TASK_LOADOUT, ids_state=ids_state)
    assert result["ok"] is True
    assert "cards" in result["result"]


def test_run_task_ehp_slice() -> None:
    ids_state = _fixture_ids_state()
    result = run_task(
        TASK_EHP_SLICE,
        {"enabled_stats": ["tower_hp"], "allow_out_of_scope": True},
        ids_state=ids_state,
    )
    assert result["ok"] is True
    assert result["result"]["stats"]


def test_run_task_max_wave() -> None:
    ids_state = _fixture_ids_state()
    spec_path = Path("tests/fixtures/specs/sample_spec.yaml")
    spec = load_problem_spec(spec_path)
    result = run_task(
        TASK_MAX_WAVE,
        {"problem_spec": spec_as_dict(spec)},
        ids_state=ids_state,
    )
    assert result["task"] == TASK_MAX_WAVE
    assert "w_max" in result


def test_run_task_rejects_unknown_args() -> None:
    ids_state = _fixture_ids_state()
    with pytest.raises(ValueError):
        run_task(TASK_BASE_STATS, {"extra": "no"}, ids_state=ids_state)
