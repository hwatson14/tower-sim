from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isclose
from typing import Any, Literal


class Rarity(Enum):
    COMMON = "Common"
    RARE = "Rare"
    EPIC = "Epic"
    LEGENDARY = "Legendary"
    MYTHIC = "Mythic"
    ANCESTRAL = "Ancestral"

    @classmethod
    def parse(cls, value: str) -> "Rarity":
        key = value.strip().lower()
        for rarity in cls:
            if rarity.value.lower() == key:
                return rarity
        raise ValueError(f"unknown module rarity: {value!r}")


RARITY_ORDER = {
    Rarity.COMMON: 0,
    Rarity.RARE: 1,
    Rarity.EPIC: 2,
    Rarity.LEGENDARY: 3,
    Rarity.MYTHIC: 4,
    Rarity.ANCESTRAL: 5,
}


class ModuleFamily(Enum):
    CANNON = "Cannon"
    ARMOR = "Armor"
    GENERATOR = "Generator"
    CORE = "Core"

    @classmethod
    def parse(cls, value: str) -> "ModuleFamily":
        key = value.strip().lower()
        for family in cls:
            if family.value.lower() == key:
                return family
        raise ValueError(f"unknown module family: {value!r}")


@dataclass(frozen=True)
class EffectSpec:
    family: ModuleFamily
    effect_id: str
    display_name: str
    values_by_rarity: dict[Rarity, float | int | str | None]
    units: str | None = None
    source_row: dict[str, str] | None = None


@dataclass(frozen=True)
class ModuleSlot:
    effect_id: str
    rarity: Rarity


@dataclass(frozen=True)
class ModuleState:
    family: ModuleFamily
    slots: tuple[ModuleSlot, ...]
    module_name: str | None = None
    is_assist: bool = False
    assist_efficiency: float | None = None

    def __post_init__(self) -> None:
        if not self.slots:
            raise ValueError("module state must have at least one slot")

    def effect_ids(self) -> tuple[str, ...]:
        return tuple(slot.effect_id for slot in self.slots)


@dataclass(frozen=True)
class BanState:
    family: ModuleFamily
    banned_effect_ids: frozenset[str] = frozenset()
    free_banned_effect_ids: frozenset[str] = frozenset()

    @property
    def all_banned_effect_ids(self) -> frozenset[str]:
        return self.banned_effect_ids | self.free_banned_effect_ids


@dataclass(frozen=True)
class DuplicatePolicy:
    """Configurable duplicate semantics; defaults are assumptions, not live certification."""

    exclude_existing_effects_from_pool: bool = True
    exclude_locked_effects_from_pool: bool = True
    dedupe_within_roll: bool = True
    slot_draw_order: Literal["ordered", "unordered"] = "unordered"

    def __post_init__(self) -> None:
        if self.slot_draw_order not in {"ordered", "unordered"}:
            raise ValueError("slot_draw_order must be 'ordered' or 'unordered'")

    def as_dict(self) -> dict[str, Any]:
        return {
            "exclude_existing_effects_from_pool": self.exclude_existing_effects_from_pool,
            "exclude_locked_effects_from_pool": self.exclude_locked_effects_from_pool,
            "dedupe_within_roll": self.dedupe_within_roll,
            "slot_draw_order": self.slot_draw_order,
            "certification_status": "assumption_uncertified",
        }


@dataclass(frozen=True)
class RerollMechanicsConfig:
    rarity_probabilities: dict[Rarity, float]
    lock_costs: dict[int, int]
    duplicate_policy: DuplicatePolicy = field(default_factory=DuplicatePolicy)

    def __post_init__(self) -> None:
        total = sum(self.rarity_probabilities.values())
        if not isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"rarity probabilities must sum to 1.0, got {total}")
        if not self.lock_costs:
            raise ValueError("lock costs cannot be empty")
        for lock_count, cost in self.lock_costs.items():
            if lock_count < 0 or cost < 0:
                raise ValueError("lock counts and lock costs must be non-negative")


@dataclass(frozen=True)
class TargetRequirement:
    effect_id: str
    min_rarity: Rarity


@dataclass(frozen=True)
class FixedTargetPolicy:
    requirements: tuple[TargetRequirement, ...]
    preserved_effect_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ExpectedCostResult:
    target_satisfied: bool
    possible: bool
    expected_shards: float
    expected_rolls: float | None
    best_locked_slot_indices: frozenset[int] | None
    per_roll_success_probability: float | None
    assumptions: dict[str, Any]
    warnings: tuple[str, ...] = ()
