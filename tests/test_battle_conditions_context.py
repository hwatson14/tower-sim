import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.battle_conditions import BCRow, BattleConditions  # noqa: E402
from tower_sim.run_context import RunContext  # noqa: E402


def test_battle_conditions_filter_by_run_context_and_tier() -> None:
    rows = [
        BCRow(
            tier="T1",
            context="farm",
            name="farm hp",
            target="tower_hp",
            op="add",
            value=10.0,
            units="abs",
        ),
        BCRow(
            tier="T1",
            context="tourney",
            name="tourney hp",
            target="tower_hp",
            op="add",
            value=20.0,
            units="abs",
        ),
        BCRow(
            tier="T2",
            context="farm",
            name="farm hp",
            target="tower_hp",
            op="add",
            value=30.0,
            units="abs",
        ),
    ]
    bc = BattleConditions(rows)

    farm_ctx = RunContext.farming("T1")
    tourney_ctx = RunContext.tournament("T1", perks_enabled=True)

    farm_only = bc.for_run_context(farm_ctx)
    tourney_only = bc.for_run_context(tourney_ctx)

    assert [row.value for row in farm_only.rows] == [10.0]
    assert [row.value for row in tourney_only.rows] == [20.0]


def test_battle_conditions_rejects_unknown_context() -> None:
    rows = [
        BCRow(
            tier="T1",
            context="invalid",
            name="bad",
            target="tower_hp",
            op="add",
            value=1.0,
            units="abs",
        )
    ]
    bc = BattleConditions(rows)
    with pytest.raises(ValueError, match="Unknown battle condition context"):
        bc.for_run_context(RunContext.farming("T1"))
