from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Tuple

from tower_sim.engines.stat_input_compiler import _UW_TRACK_SPECS, _WORKSHOP_STAT_SPECS
from tower_sim.registry.stat_registry import default_registry


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


@dataclass(frozen=True)
class StatContributorContract:
    """Machine-checkable contract for stat contributor lineage."""

    contributor: str
    canonical_stat_id: str
    reaches_stat_input: bool
    exclusion_reason: str | None = None


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


_CONTRIBUTORS: Tuple[str, ...] = (
    "workshop",
    "lab",
    "card",
    "module",
    "relic",
    "perk",
    "bc",
    "uw",
)


def _compiled_workshop_stat_ids() -> Tuple[str, ...]:
    return tuple(sorted({spec.stat_id for spec in _WORKSHOP_STAT_SPECS.values()}))


def _compiled_uw_stat_ids() -> Tuple[str, ...]:
    stat_ids = set()
    for tracks in _UW_TRACK_SPECS.values():
        for spec in tracks.values():
            stat_ids.add(spec.stat_id)
            stat_ids.add(f"{spec.stat_id}_next_cost")
    return tuple(sorted(stat_ids))


# Explicit reaches-stat-input declarations with provenance in existing runtime wiring.
# All unspecified contributor/stat combinations fail-closed as excluded.
_REACHES_STAT_INPUT: Dict[str, Tuple[str, ...]] = {
    **{stat_id: ("workshop",) for stat_id in _compiled_workshop_stat_ids()},
    **{stat_id: ("uw",) for stat_id in _compiled_uw_stat_ids()},
    "tower_hp": ("workshop",),
    "tower_regen": ("workshop",),
    "wall_hp": ("workshop",),
    "wall_regen": ("workshop",),
    "def_pct": ("workshop", "bc"),
    "thorns_damage_mult": ("workshop", "bc"),
    "orb_damage_mult": ("bc",),
    "death_ray_damage_mult": ("bc",),
    "plasma_cannon_damage_mult": ("bc",),
    "knockback_mult": ("bc",),
    "eals_pct": ("workshop", "lab"),
    "ehls_pct": ("workshop", "lab"),
    "wave_attack_index": ("workshop", "lab"),
    "wave_health_index": ("workshop", "lab"),
    "tower_damage": ("workshop", "lab", "card", "module", "relic", "perk"),
    "tower_attack_speed": ("workshop", "lab", "card", "module", "relic"),
    "tower_crit_chance": ("workshop", "card", "module", "relic"),
    "tower_crit_multiplier": ("workshop", "module"),
    "tower_dps": ("workshop", "lab", "card", "module", "relic", "perk"),
}


def _excluded_reason(contributor: str, stat_id: str) -> str:
    if contributor == "bc":
        return "excluded:no_authoritative_bc_mapping_for_stat"
    if contributor == "uw":
        return "excluded:no_authoritative_uw_mapping_for_stat"
    return "excluded:not_wired_to_canonical_stat_input"


# Authoritative lineage manifest for all canonical registry stat IDs.
# Scope: contract declarations + CI validation gates.
#
# Contributor semantics:
# - reaches_stat_input=True: contributor must flow into canonical StatInput composition.
# - reaches_stat_input=False: contributor is explicitly excluded until deterministic,
#   authoritative mechanics wiring exists; exclusion must state a fail-closed reason.
_ALL_STAT_LINEAGE: Dict[str, Tuple[StatContributorContract, ...]] = {}
for stat_def in default_registry().all_defs():
    stat_id = stat_def.stat_id
    reaches = set(_REACHES_STAT_INPUT.get(stat_id, tuple()))
    _ALL_STAT_LINEAGE[stat_id] = tuple(
        StatContributorContract(
            contributor=contributor,
            canonical_stat_id=stat_id,
            reaches_stat_input=contributor in reaches,
            exclusion_reason=None if contributor in reaches else _excluded_reason(contributor, stat_id),
        )
        for contributor in _CONTRIBUTORS
    )


# IDS section linkage for contributor-name contract gates.
_CONTRIBUTOR_IDS_SECTIONS: Dict[str, Tuple[str, ...]] = {
    "workshop": ("WS", "WS+"),
    "lab": ("Labs",),
    "card": ("Cards",),
    "module": ("Modules",),
    "relic": ("Relics",),
    "perk": tuple(),
    "bc": tuple(),
    "uw": ("UWs",),
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


def stat_lineage_manifest() -> Mapping[str, Tuple[StatContributorContract, ...]]:
    return _ALL_STAT_LINEAGE


def contributor_ids_sections() -> Mapping[str, Tuple[str, ...]]:
    return _CONTRIBUTOR_IDS_SECTIONS


def missing_required_combat_stats(stat_ids: Iterable[str]) -> Tuple[str, ...]:
    present = set(stat_ids)
    missing = sorted(set(_CANONICAL_REQUIRED_COMBAT_STAT_IDS) - present)
    return tuple(missing)


__all__ = [
    "CombatContributorCoverage",
    "StatContributorContract",
    "contributor_ids_sections",
    "declared_combat_stat_coverage",
    "missing_required_combat_stats",
    "required_combat_stat_ids",
    "required_survivability_stat_ids",
    "stat_lineage_manifest",
]
