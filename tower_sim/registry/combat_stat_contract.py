from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Tuple


# Provenance: ARCHITECTURE.md "Evaluator Contracts" and survivability requirements
# in `tower_sim/evaluators/max_wave.py` define these as required combat stats.
_CANONICAL_REQUIRED_COMBAT_STAT_IDS: Tuple[str, ...] = (
    "tower_hp",
    "tower_regen",
    "def_pct",
    "wall_hp",
    "wall_regen",
    "thorns_damage_mult",
)


@dataclass(frozen=True)
class CombatContributorCoverage:
    """Declared contributor coverage contract for canonical combat stats."""

    base: bool
    loadout: bool
    enhancement: bool
    tier: bool
    derived: bool


# Phase-A contract: each canonical survivability stat must declare contributor coverage.
# This is a declaration/validation contract only; composition wiring follows in later phases.
_CANONICAL_COVERAGE: Dict[str, CombatContributorCoverage] = {
    "tower_hp": CombatContributorCoverage(
        base=True,
        loadout=True,
        enhancement=True,
        tier=True,
        derived=True,
    ),
    "tower_regen": CombatContributorCoverage(
        base=True,
        loadout=True,
        enhancement=True,
        tier=True,
        derived=True,
    ),
    "def_pct": CombatContributorCoverage(
        base=True,
        loadout=True,
        enhancement=True,
        tier=True,
        derived=True,
    ),
    "wall_hp": CombatContributorCoverage(
        base=True,
        loadout=True,
        enhancement=True,
        tier=True,
        derived=True,
    ),
    "wall_regen": CombatContributorCoverage(
        base=True,
        loadout=True,
        enhancement=True,
        tier=True,
        derived=True,
    ),
    "thorns_damage_mult": CombatContributorCoverage(
        base=True,
        loadout=True,
        enhancement=True,
        tier=True,
        derived=True,
    ),
}


def required_combat_stat_ids() -> Tuple[str, ...]:
    return _CANONICAL_REQUIRED_COMBAT_STAT_IDS


# Boss model currently also consumes plasma-cannon multiplier in survivability paths.
_OPTIONAL_SURVIVABILITY_STAT_IDS: Tuple[str, ...] = (
    "plasma_cannon_damage_mult",
)


def required_survivability_stat_ids(*, include_optional_offense: bool = False) -> Tuple[str, ...]:
    if include_optional_offense:
        return _CANONICAL_REQUIRED_COMBAT_STAT_IDS + _OPTIONAL_SURVIVABILITY_STAT_IDS
    return _CANONICAL_REQUIRED_COMBAT_STAT_IDS


def declared_combat_stat_coverage() -> Mapping[str, CombatContributorCoverage]:
    return _CANONICAL_COVERAGE


def missing_required_combat_stats(stat_ids: Iterable[str]) -> Tuple[str, ...]:
    present = set(stat_ids)
    missing = sorted(set(_CANONICAL_REQUIRED_COMBAT_STAT_IDS) - present)
    return tuple(missing)


__all__ = [
    "CombatContributorCoverage",
    "declared_combat_stat_coverage",
    "missing_required_combat_stats",
    "required_combat_stat_ids",
    "required_survivability_stat_ids",
]
