from __future__ import annotations

from pathlib import Path
import sys

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.engines.free_upgrades import FreeUpgradeChances  # noqa: E402
from tower_sim.engines.workshop_progression import (  # noqa: E402
    AllocationPolicyError,
    WSCategory,
    WorkshopStat,
    simulate_workshop_progression,
)


def _all_to_first(available: list[WorkshopStat], upgrades: float) -> dict[str, float]:
    if upgrades <= 0 or not available:
        return {}
    return {available[0].name: upgrades}


def test_requires_allocation_policy() -> None:
    stats = [
        WorkshopStat(
            name="Damage",
            category=WSCategory.OFFENSE,
            start_level=0,
            end_level=5,
            max_level=5,
        )
    ]
    chances = FreeUpgradeChances(attack=1.0, defense=0.0, utility=0.0)

    with pytest.raises(AllocationPolicyError):
        simulate_workshop_progression(stats, chances, max_waves=1)


def test_progression_with_explicit_policy() -> None:
    stats = [
        WorkshopStat(
            name="Damage",
            category=WSCategory.OFFENSE,
            start_level=0,
            end_level=5,
            max_level=5,
        ),
        WorkshopStat(
            name="Speed",
            category=WSCategory.OFFENSE,
            start_level=0,
            end_level=5,
            max_level=5,
        ),
    ]
    chances = FreeUpgradeChances(attack=1.0, defense=0.0, utility=0.0)

    result = simulate_workshop_progression(
        stats,
        chances,
        max_waves=2,
        allocation_policy=_all_to_first,
    )

    assert result.levels["Damage"] == [0.0, 1.0, 2.0]
    assert result.levels["Speed"] == [0.0, 0.0, 0.0]
    assert result.waves_to_end["Damage"] is None
