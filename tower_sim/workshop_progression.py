from __future__ import annotations

"""Workshop progression during a run, driven by Free Upgrades.

Important constraints (from your spec / conversation):
- Workshop has two levels per stat in IDS: ¢ (start-of-run) and $ (end-of-run).
- Wave-based increases during a run must follow Free Upgrade logic.

This module implements a deterministic *expected-value* simulator.

Design note:
- The exact in-game allocation rule for which stat gets a free upgrade
  (uniform among non-maxed stats? weighted? fixed order?) must be sourced
  from the wiki or Effective Paths reference. Until then, we treat the
  allocation policy as an injected strategy.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Callable, Optional

from .free_upgrades import FreeUpgradeChances, expected_upgrades_per_wave


class WSCategory(str, Enum):
    OFFENSE = "offense"
    DEFENSE = "defense"
    UTILITY = "utility"


@dataclass
class WorkshopStat:
    name: str
    category: WSCategory
    start_level: int
    end_level: int
    max_level: int
    unlocked: bool = True

    def remaining(self) -> int:
        if not self.unlocked:
            return 0
        return max(0, min(self.end_level, self.max_level) - min(self.start_level, self.max_level))


AllocationPolicy = Callable[[List[WorkshopStat], float], Dict[str, float]]


class AllocationPolicyError(ValueError):
    pass


def uniform_allocation(available: List[WorkshopStat], upgrades: float) -> Dict[str, float]:
    """Allocate expected upgrades uniformly across available, non-maxed stats.

    This helper is not used by default. Callers must provide a policy with
    authoritative provenance (sheet/wiki).
    """
    if upgrades <= 0 or not available:
        return {}
    per = upgrades / len(available)
    return {s.name: per for s in available}


@dataclass
class WorkshopProgressionResult:
    # levels[stat_name][wave] = expected level (float) at end of that wave
    levels: Dict[str, List[float]]
    # wave where stat reaches end_level (or max_level cap), None if not reached within horizon
    waves_to_end: Dict[str, Optional[int]]


def simulate_workshop_progression(
    stats: List[WorkshopStat],
    chances: FreeUpgradeChances,
    max_waves: int = 20000,
    allocation_policy: AllocationPolicy | None = None,
    waves_skipped_per_wave: float = 0.0,
) -> WorkshopProgressionResult:
    """Deterministic expected-value workshop progression.

    Mechanics implemented:
    - each wave produces expected upgrades per category based on free-upgrade chance
    - upgrades are allocated across non-maxed, unlocked stats per category using allocation_policy
    - stats are treated continuously (expected levels can be fractional)

    Not yet implemented:
    - wave skip extra triggers (plumbed as waves_skipped_per_wave, but set 0 by default)
    - selection rules (requires wiki or sheet verification)
    """
    if allocation_policy is None:
        raise AllocationPolicyError(
            "Workshop allocation policy required (fail-closed). "
            "Provide a policy backed by authoritative source."
        )

    # initialise level tracks
    level_map: Dict[str, float] = {}
    tracks: Dict[str, List[float]] = {}
    targets: Dict[str, float] = {}

    for s in stats:
        lvl0 = float(min(s.start_level, s.max_level)) if s.unlocked else 0.0
        level_map[s.name] = lvl0
        tracks[s.name] = [lvl0]  # wave 0
        targets[s.name] = float(min(s.end_level, s.max_level)) if s.unlocked else 0.0

    waves_to_end: Dict[str, Optional[int]] = {s.name: (0 if level_map[s.name] >= targets[s.name] else None) for s in stats}

    def category_chance(cat: WSCategory) -> float:
        if cat == WSCategory.OFFENSE:
            return chances.attack
        if cat == WSCategory.DEFENSE:
            return chances.defense
        if cat == WSCategory.UTILITY:
            return chances.utility
        raise ValueError(f"Unknown category: {cat}")

    for w in range(1, max_waves + 1):
        # stop early if all reached
        if all(level_map[name] >= targets[name] for name in level_map):
            # still extend tracks to same length for completeness? no; we stop.
            break

        # compute expected upgrades per category
        for cat in (WSCategory.OFFENSE, WSCategory.DEFENSE, WSCategory.UTILITY):
            chance = category_chance(cat)
            upgrades = expected_upgrades_per_wave(chance, waves_skipped=waves_skipped_per_wave)

            # available stats in this category that can still increase
            avail = [
                s for s in stats
                if s.category == cat
                and s.unlocked
                and level_map[s.name] < targets[s.name]
            ]
            alloc = allocation_policy(avail, upgrades)
            _validate_allocation(alloc, avail, upgrades)
            for name, inc in alloc.items():
                if inc <= 0:
                    continue
                level_map[name] = min(targets[name], level_map[name] + inc)

        # record after this wave
        for name in tracks:
            tracks[name].append(level_map[name])
            if waves_to_end[name] is None and level_map[name] >= targets[name]:
                waves_to_end[name] = w

    return WorkshopProgressionResult(levels=tracks, waves_to_end=waves_to_end)


def _validate_allocation(
    allocation: Dict[str, float],
    available: List[WorkshopStat],
    upgrades: float,
) -> None:
    available_names = {stat.name for stat in available}
    if not allocation:
        return
    if any(name not in available_names for name in allocation):
        unknown = sorted(set(allocation).difference(available_names))
        raise AllocationPolicyError(f"Allocation includes unknown stats: {unknown}")
    if any(value < 0 for value in allocation.values()):
        raise AllocationPolicyError("Allocation cannot include negative upgrades.")
    total = sum(allocation.values())
    if total - upgrades > 1e-6:
        raise AllocationPolicyError(
            f"Allocation exceeds upgrades: allocated {total} > available {upgrades}."
        )
