from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.registry.stat_registry import Phase, default_registry  # noqa: E402
from tower_sim.util.statbook import CanonicalStatRow  # noqa: E402
from tower_sim.engines.statbook_builder import build_canonical_statbook  # noqa: E402


def _sample_row(**overrides: object) -> CanonicalStatRow:
    data = {
        "stat_id": "tower_hp",
        "phase": Phase.START_OF_RUN,
        "base_value": Decimal("10"),
        "loadout_delta_modules": Decimal("1"),
        "loadout_delta_cards": Decimal("2"),
        "loadout_delta_bots": Decimal("3"),
        "loadout_delta_guardians": Decimal("4"),
        "loadout_delta_other": Decimal("5"),
        "enhancement_multiplier": Decimal("1.0"),
        "tier_rule_delta_or_multiplier": Decimal("0"),
        "final_value": Decimal("25"),
        "provenance": "reference:statbook_v6_reference.xlsx",
    }
    data.update(overrides)
    return CanonicalStatRow(**data)


def test_canonical_statbook_csv_headers(tmp_path: Path) -> None:
    registry = default_registry()
    statbook = build_canonical_statbook([_sample_row()], registry=registry)
    path = tmp_path / "statbook_canonical.csv"
    statbook.to_csv(path)
    header = path.read_text().splitlines()[0]
    assert header == (
        "stat_id,phase,base_value,loadout_delta,loadout_delta_modules,"
        "loadout_delta_cards,loadout_delta_bots,loadout_delta_guardians,"
        "loadout_delta_other,enhancement_multiplier,tier_rule_delta_or_multiplier,"
        "final_value,provenance"
    )


def test_canonical_statbook_unknown_stat_raises() -> None:
    with pytest.raises(KeyError):
        build_canonical_statbook([_sample_row(stat_id="unknown_stat")])


def test_canonical_statbook_requires_full_loadout_breakdown() -> None:
    row = _sample_row(loadout_delta_cards=None)
    with pytest.raises(ValueError, match="loadout delta components"):
        build_canonical_statbook([row])
