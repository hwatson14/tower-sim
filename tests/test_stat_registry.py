import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.stat_registry import (  # noqa: E402
    Phase,
    StatDef,
    StatKind,
    StatRegistry,
    StatScope,
    Unit,
    UnknownStatError,
    default_registry,
)
from tower_sim.statbook import StatBook, StatRow  # noqa: E402


def test_registry_unknown_stat_raises() -> None:
    registry = default_registry()
    with pytest.raises(UnknownStatError):
        registry.validate_stat_id("typo_stat")


def test_statbook_rejects_unknown_stat() -> None:
    registry = default_registry()
    row = StatRow(
        stat_name="unknown_stat",
        phase=Phase.START_OF_RUN,
        value="1",
        source="test",
    )
    with pytest.raises(UnknownStatError):
        registry.validate_stat_id(row.stat_name)


def test_registry_export_stable() -> None:
    registry = default_registry()
    stat_ids = [definition.stat_id for definition in registry.all_defs()]
    assert stat_ids == sorted(stat_ids)
    required = {"tower_hp", "tower_regen", "def_pct", "wall_hp", "wall_regen"}
    assert required.issubset(stat_ids)


def test_definitions_export_written(tmp_path: Path) -> None:
    statbook = StatBook(
        rows=[
            StatRow(
                stat_name="tower_hp",
                phase=Phase.START_OF_RUN,
                value="1",
                source="test",
            )
        ],
    )
    statbook_path = tmp_path / "statbook.csv"
    statbook.to_csv(statbook_path)
    content = statbook_path.read_text()
    assert "stat_name" in content
    assert "tower_hp" in content
