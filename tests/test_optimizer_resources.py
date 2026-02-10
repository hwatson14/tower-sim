from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path

import pytest

from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.api import TASK_OPTIMIZE_COINS, TASK_OPTIMIZE_LABS, TASK_OPTIMIZE_STONES, run_task
from tower_sim.run.optimizer_engine import INTERNAL_PRESET_SEQUENCE


def _to_jsonable(value):
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _snapshot_payload():
    snapshot = compile_account_snapshot(parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv")))
    return {"snapshot": _to_jsonable(snapshot)}


def test_optimize_stones_fails_closed_when_required_tables_missing() -> None:
    result = run_task(
        TASK_OPTIMIZE_STONES,
        {
            "objective": "MAX_WAVE",
            "account_snapshot": _snapshot_payload(),
        },
    )
    assert result["ok"] is False
    assert result["fail_closed"] is True
    assert any(item.startswith("missing_table:") for item in result["missing"])


def test_optimize_stones_econ_objective_is_v2_only() -> None:
    result = run_task(
        TASK_OPTIMIZE_STONES,
        {
            "objective": "ECON_PER_HOUR",
            "account_snapshot": _snapshot_payload(),
        },
    )
    assert result["ok"] is False
    assert result["fail_closed"] is True
    assert "econ_evaluator_not_implemented" in result["missing"]


@pytest.mark.parametrize("task", [TASK_OPTIMIZE_COINS, TASK_OPTIMIZE_LABS])
def test_optimize_non_stone_returns_visible_ineligible_rows(task: str) -> None:
    result = run_task(
        task,
        {
            "objective": "MAX_WAVE",
            "account_snapshot": _snapshot_payload(),
            "top_n": 2,
        },
    )
    assert result["ok"] is True
    assert result["fail_closed"] is False
    tables = result["result"]["tables"]

    assert result["result"]["data_complete"] is False
    assert result["result"]["incomplete_reasons"]
    assert [table["preset_name"] for table in tables] == list(INTERNAL_PRESET_SEQUENCE)
    for table in tables:
        assert "preset_label" in table
        rows = table["ranked_actions"]
        assert rows
        assert all(row["eligible"] is False for row in rows)
        assert all(row["roi"] is None for row in rows)


def test_optimizer_top_n_validation() -> None:
    with pytest.raises(ValueError, match="top_n must be a positive integer"):
        run_task(
            TASK_OPTIMIZE_COINS,
            {
                "objective": "MAX_WAVE",
                "account_snapshot": _snapshot_payload(),
                "top_n": 0,
            },
        )


def test_snapshot_patch_unknown_stat_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unknown lab stat_id in snapshot_patch"):
        run_task(
            TASK_OPTIMIZE_COINS,
            {
                "objective": "MAX_WAVE",
                "account_snapshot": _snapshot_payload(),
                "snapshot_patch": {
                    "type": "snapshot_patch",
                    "labs": [{"stat_id": "NOT_A_REAL_LAB", "delta_levels": 1}],
                },
            },
        )
