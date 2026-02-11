from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Tuple

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


# Explicit reaches-stat-input declarations with provenance in existing runtime wiring.
# All unspecified contributor/stat combinations fail-closed as excluded.
_REACHES_STAT_INPUT: Dict[str, Tuple[str, ...]] = {
    "tower_hp": ("workshop",),
    "tower_regen": ("workshop",),
    "def_pct": ("workshop", "bc"),
    "wall_hp": ("workshop",),
    "wall_regen": ("workshop",),
    "thorns_damage_mult": ("workshop", "bc"),
    "eals_pct": ("workshop",),
    "ehls_pct": ("workshop",),
    "orb_damage_mult": ("bc",),
    "death_ray_damage_mult": ("bc",),
    "plasma_cannon_damage_mult": ("bc",),
    "knockback_mult": ("bc",),
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


# Canonical MAX_WAVE stat inputs currently required by canonical stat-input assembly.
# Provenance: `tower_sim/engines/combat_stat_derivation.py::_missing_required_stat_inputs`.
_MAX_WAVE_REQUIRED_STAT_INPUT_IDS: Tuple[str, ...] = (
    "eals_pct",
    "ehls_pct",
    "orb_damage_mult",
    "death_ray_damage_mult",
    "plasma_cannon_damage_mult",
    "knockback_mult",
    *_CANONICAL_REQUIRED_COMBAT_STAT_IDS,
)


def required_survivability_stat_ids(*, include_optional_offense: bool = False) -> Tuple[str, ...]:
    if include_optional_offense:
        return _CANONICAL_REQUIRED_COMBAT_STAT_IDS + _OPTIONAL_SURVIVABILITY_STAT_IDS
    return _CANONICAL_REQUIRED_COMBAT_STAT_IDS


def required_max_wave_stat_input_ids() -> Tuple[str, ...]:
    return _MAX_WAVE_REQUIRED_STAT_INPUT_IDS


def ordered_stat_lineage_sections() -> Tuple[Tuple[str, Tuple[str, ...]], ...]:
    """Return stat-lineage sections with max-wave-required IDs first."""

    required = tuple(required_max_wave_stat_input_ids())
    required_set = set(required)
    other = tuple(
        definition.stat_id
        for definition in default_registry().all_defs()
        if definition.stat_id not in required_set
    )
    return (
        ("required_max_wave_stat_inputs", required),
        ("other_registry_stats", other),
    )


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
    "required_max_wave_stat_input_ids",
    "ordered_stat_lineage_sections",
    "stat_lineage_manifest",
]
