from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable

from tower_sim.run_context import RunContext
from tower_sim.wiki.perks import (
    apply_standard_perk_bonus_additive_checked,
    apply_standard_perk_bonus_multiplicative_checked,
)


class PerkMode(str, Enum):
    MULTIPLICATIVE = "multiplicative"
    ADDITIVE = "additive"


class InvalidPerkError(ValueError):
    pass


@dataclass(frozen=True)
class PerkInput:
    name: str
    perk_base: float
    quantity: int
    standard_perk_bonus: float
    mode: PerkMode
    provenance: str


@dataclass(frozen=True)
class PerkResult:
    name: str
    mode: PerkMode
    value: float
    provenance: str


class PerkEngine:
    def apply(
        self,
        context: RunContext,
        perks: Iterable[PerkInput],
    ) -> Dict[str, PerkResult]:
        results: Dict[str, PerkResult] = {}
        for perk in perks:
            _validate_perk(perk)
            value = _apply_perk(context, perk)
            results[perk.name] = PerkResult(
                name=perk.name,
                mode=perk.mode,
                value=value,
                provenance=perk.provenance,
            )
        return results


def _apply_perk(context: RunContext, perk: PerkInput) -> float:
    if perk.mode == PerkMode.MULTIPLICATIVE:
        return apply_standard_perk_bonus_multiplicative_checked(
            context,
            perk.perk_base,
            perk.quantity,
            perk.standard_perk_bonus,
        )
    if perk.mode == PerkMode.ADDITIVE:
        return apply_standard_perk_bonus_additive_checked(
            context,
            perk.perk_base,
            perk.quantity,
            perk.standard_perk_bonus,
        )
    raise InvalidPerkError(f"Unknown perk mode: {perk.mode!r}")


def _validate_perk(perk: PerkInput) -> None:
    if perk.name.strip() == "":
        raise InvalidPerkError("Perk name is required.")
    if perk.quantity < 0:
        raise InvalidPerkError("Perk quantity cannot be negative.")
    if perk.provenance.strip() == "":
        raise InvalidPerkError("Perk provenance is required.")
