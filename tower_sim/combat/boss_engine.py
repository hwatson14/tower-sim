from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


class MissingMechanicError(RuntimeError):
    pass


@dataclass(frozen=True)
class BossCombatInputs:
    wave: int
    wave_damage: float
    tower_hp: float
    tower_regen: float
    defense_pct: float
    thorns_pct: Optional[float]
    package_chance: Optional[float]
    package_heal: Optional[float]
    damage_reduction: Optional[float]
    provenance: str


class BossCombatEngine:
    """Fail-closed boss combat engine placeholder.

    This engine validates required inputs but raises until authoritative
    combat mechanics are supplied (PC + thorns + regen + DR).
    """

    def evaluate(self, inputs: BossCombatInputs) -> None:
        missing = _missing_inputs(inputs)
        if missing:
            raise MissingMechanicError(
                "Missing required boss combat inputs: " + ", ".join(missing)
            )
        raise MissingMechanicError(
            "Boss combat mechanics not implemented. "
            "Provide authoritative formulas for PC, thorns, regen, and DR."
        )


def _missing_inputs(inputs: BossCombatInputs) -> List[str]:
    missing: List[str] = []
    if inputs.wave <= 0:
        missing.append("wave")
    if inputs.wave_damage is None:
        missing.append("wave_damage")
    if inputs.tower_hp is None:
        missing.append("tower_hp")
    if inputs.tower_regen is None:
        missing.append("tower_regen")
    if inputs.defense_pct is None:
        missing.append("defense_pct")
    if inputs.thorns_pct is None:
        missing.append("thorns_pct")
    if inputs.package_chance is None:
        missing.append("package_chance")
    if inputs.package_heal is None:
        missing.append("package_heal")
    if inputs.damage_reduction is None:
        missing.append("damage_reduction")
    if inputs.provenance.strip() == "":
        missing.append("provenance")
    return missing
