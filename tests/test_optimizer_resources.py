from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path

import pytest

from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.api import TASK_OPTIMIZE_COINS, TASK_OPTIMIZE_LABS, TASK_OPTIMIZE_STONES, run_task
from tower_sim.run.optimizer_engine import INTERNAL_PRESET_SEQUENCE, _parse_uw_rows


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


@pytest.fixture
def stub_max_wave_evaluator(monkeypatch: pytest.MonkeyPatch) -> None:
    def _evaluate(_self, _problem_spec, snapshot):
        unlocked_masteries = sum(1 for card in snapshot.cards_inventory.values() if card.mastery_unlocked)
        unlocked_assist_slots = sum(1 for state in snapshot.module_system_state.values() if state.assist_unlocked)
        uw_state = _parse_uw_rows(snapshot)
        uw_levels = sum(track["current_level"] for track in uw_state["uw_tracks"])
        uw_plus_levels = sum(track["current_level"] for track in uw_state["uw_plus_tracks"])
        return float(
            unlocked_masteries
            + unlocked_assist_slots
            + (10 * uw_state["uw_unlocked_count"])
            + (25 * uw_state["uw_plus_unlocked_count"])
            + (0.01 * uw_levels)
            + (0.001 * uw_plus_levels)
        )

    monkeypatch.setattr("tower_sim.run.optimizer_engine.MaxWaveAdapter.evaluate", _evaluate)


def test_optimize_stones_uses_assist_tables_and_returns_ranked_rows(stub_max_wave_evaluator: None) -> None:
    result = run_task(
        TASK_OPTIMIZE_STONES,
        {
            "objective": "MAX_WAVE",
            "account_snapshot": _snapshot_payload(),
            "top_n": 400,
        },
    )
    assert result["ok"] is True
    assert result["fail_closed"] is False
    assert result["result"]["data_complete"] is True
    assert result["result"]["incomplete_reasons"] == []
    rows = result["result"]["tables"][0]["ranked_actions"]
    assert any(row["action_id"].startswith("assist_efficiency_upgrade::") for row in rows)
    assert any(row["action_id"].startswith("assist_rarity_upgrade::") for row in rows)


def test_optimize_stones_runs_max_wave_for_integrated_actions(stub_max_wave_evaluator: None) -> None:
    result = run_task(
        TASK_OPTIMIZE_STONES,
        {
            "objective": "MAX_WAVE",
            "account_snapshot": _snapshot_payload(),
            "top_n": 400,
        },
    )

    assert result["ok"] is True
    rows = result["result"]["tables"][0]["ranked_actions"]
    assert any(row["eligible"] is True for row in rows)
    assert any(row["candidate_value"] is not None for row in rows if row["eligible"] is True)


def test_optimize_stones_scopes_mastery_rows_to_table_preset(stub_max_wave_evaluator: None) -> None:
    result = run_task(
        TASK_OPTIMIZE_STONES,
        {
            "objective": "MAX_WAVE",
            "account_snapshot": _snapshot_payload(),
            "top_n": 200,
        },
    )

    tables = {table["preset_name"]: table for table in result["result"]["tables"]}
    for preset_name, table in tables.items():
        mastery_rows = [
            row
            for row in table["ranked_actions"]
            if row["action_id"].startswith("mastery_unlock::")
        ]
        if mastery_rows:
            assert all(row["action_id"].split("::", 2)[1] == preset_name for row in mastery_rows)




def test_optimize_stones_uw_actions_improve_stubbed_candidate_value(stub_max_wave_evaluator: None) -> None:
    result = run_task(
        TASK_OPTIMIZE_STONES,
        {
            "objective": "MAX_WAVE",
            "account_snapshot": _snapshot_payload(),
            "top_n": 400,
        },
    )

    table = result["result"]["tables"][0]
    baseline = table["baseline_value"]
    uw_rows = [row for row in table["ranked_actions"] if row["action_id"].startswith(("uw_unlock::", "uw_plus_unlock::", "uw_track_upgrade::", "uw_plus_track_upgrade::"))]

    assert baseline is not None
    assert uw_rows
    assert any(row["candidate_value"] is not None and row["candidate_value"] > baseline for row in uw_rows)

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


def test_assist_multiplier_and_substat_efficiency_use_same_cost_table(stub_max_wave_evaluator: None) -> None:
    result = run_task(
        TASK_OPTIMIZE_STONES,
        {
            "objective": "MAX_WAVE",
            "account_snapshot": _snapshot_payload(),
            "top_n": 400,
        },
    )
    table = result["result"]["tables"][0]
    rows = {row["action_id"]: row for row in table["ranked_actions"]}

    multiplier = rows["assist_efficiency_upgrade::Generator::multiplier::10"]
    substat = rows["assist_efficiency_upgrade::Generator::substat::10"]

    assert multiplier["notes"] == "assist_efficiency_upgrade_costs_v1"
    assert substat["notes"] == "assist_efficiency_upgrade_costs_v1"
    assert multiplier["cost"] == substat["cost"]


def test_optimize_stones_includes_uw_and_uwplus_rows(stub_max_wave_evaluator: None) -> None:
    result = run_task(
        TASK_OPTIMIZE_STONES,
        {
            "objective": "MAX_WAVE",
            "account_snapshot": _snapshot_payload(),
            "top_n": 400,
        },
    )
    rows = result["result"]["tables"][0]["ranked_actions"]
    assert any(row["action_id"].startswith("uw_unlock::") for row in rows)
    assert any(row["action_id"].startswith("uw_track_upgrade::") for row in rows)
    assert any(row["action_id"].startswith("uw_plus_unlock::") for row in rows)
    uw_rows = [
        row
        for row in rows
        if row["action_id"].startswith(("uw_unlock::", "uw_track_upgrade::", "uw_plus_unlock::", "uw_plus_track_upgrade::"))
    ]
    assert uw_rows
    assert all(row["eligible"] is True for row in uw_rows)
    assert any(row["candidate_value"] is not None for row in uw_rows)
