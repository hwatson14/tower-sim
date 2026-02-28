import sys
from decimal import Decimal
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.registry.stat_registry import (  # noqa: E402
    Phase,
    UnknownStatError,
    default_registry,
)
from tower_sim.util.statbook import StatBook, StatRow  # noqa: E402


def _row(stat_id: str) -> StatRow:
    return StatRow(
        stat_id=stat_id,
        phase=Phase.START_OF_RUN,
        base_value=Decimal("1"),
        loadout_delta_modules=Decimal("0"),
        loadout_delta_cards=Decimal("0"),
        loadout_delta_bots=Decimal("0"),
        loadout_delta_guardians=Decimal("0"),
        loadout_delta_other=Decimal("0"),
        enhancement_multiplier=Decimal("1"),
        tier_rule_delta_or_multiplier=Decimal("0"),
        final_value=Decimal("1"),
        provenance="test",
    )


def test_registry_unknown_stat_raises() -> None:
    registry = default_registry()
    with pytest.raises(UnknownStatError):
        registry.validate_stat_id("typo_stat")


def test_statbook_rejects_unknown_stat() -> None:
    registry = default_registry()
    row = _row("unknown_stat")
    with pytest.raises(UnknownStatError):
        registry.validate_stat_id(row.stat_id)


def test_registry_export_stable() -> None:
    registry = default_registry()
    stat_ids = [definition.stat_id for definition in registry.all_defs()]
    assert stat_ids == sorted(stat_ids)
    required = {"tower_hp", "tower_regen", "def_pct", "wall_hp", "wall_regen", "bot_flame_damage", "golden_tower_duration"}
    assert required.issubset(stat_ids)


def test_definitions_export_written(tmp_path: Path) -> None:
    statbook = StatBook(rows=[_row("tower_hp")])
    statbook_path = tmp_path / "statbook.csv"
    statbook.to_csv(statbook_path)
    content = statbook_path.read_text()
    assert "loadout_delta_modules" in content
    assert "tower_hp" in content
