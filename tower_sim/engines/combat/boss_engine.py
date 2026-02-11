from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple


class MissingMechanicError(RuntimeError):
    pass


class BossCombatError(RuntimeError):
    pass


@dataclass(frozen=True)
class BossCombatInputs:
    wave: int
    wave_damage: float
    tower_hp: float
    tower_regen: float
    defense_pct: float
    thorns_pct: Optional[float]
    pc_frac: Optional[float]
    pc_boss_mult: Optional[float]
    package_chance: Optional[float]
    package_heal: Optional[float]
    damage_reduction: Optional[float]
    provenance: str


@dataclass(frozen=True)
class BossCombatResult:
    """Boss combat survivability output (v1 minimal)."""

    effective_damage_per_sec: float
    effective_regen_per_sec: float
    net_damage_per_sec: float
    time_to_death_sec: float
    boss_hp_frac_damage_per_hit: float
    boss_hp_remaining_mult_per_hit: float
    defaults_used: Tuple[str, ...]


class BossCombatEngine:
    """Boss combat engine (v1 minimal, deterministic).

    Mechanics implemented are based on the fail-closed combat model structure in
    `tables/combat_model_authoritative.zip` and the Plasma Cannon card effect
    table in `tables/cache/wiki/cards_rare.csv` (percent-current damage).
    """

    def evaluate(self, inputs: BossCombatInputs) -> BossCombatResult:
        missing = _missing_inputs(inputs)
        if missing:
            raise MissingMechanicError(
                "Missing required boss combat inputs: " + ", ".join(missing)
            )
        defaults_used: List[str] = []
        package_chance = _default_optional(
            inputs.package_chance, 0.0, "package_chance", defaults_used
        )
        package_heal = _default_optional(
            inputs.package_heal, 0.0, "package_heal", defaults_used
        )
        damage_reduction = _default_optional(
            inputs.damage_reduction, 0.0, "damage_reduction", defaults_used
        )
        pc_frac = _default_optional(inputs.pc_frac, 0.0, "pc_frac", defaults_used)
        pc_boss_mult = _default_optional(
            inputs.pc_boss_mult, 1.0, "pc_boss_mult", defaults_used
        )

        thorns_frac = float(inputs.thorns_pct)
        _validate_fraction("defense_pct", inputs.defense_pct)
        _validate_fraction("damage_reduction", damage_reduction)
        _validate_fraction("thorns_pct", thorns_frac)
        _validate_fraction("pc_frac", pc_frac)

        incoming_damage = inputs.wave_damage
        reduced_damage = incoming_damage * (1.0 - inputs.defense_pct)
        effective_damage = reduced_damage * (1.0 - damage_reduction)

        package_regen = package_chance * package_heal
        effective_regen = inputs.tower_regen + package_regen
        net_damage = effective_damage - effective_regen
        time_to_death = float("inf") if net_damage <= 0 else inputs.tower_hp / net_damage

        boss_hp_frac_damage = thorns_frac + (pc_frac * pc_boss_mult)
        boss_hp_remaining_mult = max(0.0, 1.0 - boss_hp_frac_damage)

        return BossCombatResult(
            effective_damage_per_sec=effective_damage,
            effective_regen_per_sec=effective_regen,
            net_damage_per_sec=net_damage,
            time_to_death_sec=time_to_death,
            boss_hp_frac_damage_per_hit=boss_hp_frac_damage,
            boss_hp_remaining_mult_per_hit=boss_hp_remaining_mult,
            defaults_used=tuple(defaults_used),
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
    if inputs.provenance.strip() == "":
        missing.append("provenance")
    return missing


def _default_optional(
    value: Optional[float],
    default: float,
    name: str,
    defaults_used: List[str],
) -> float:
    if value is None:
        defaults_used.append(name)
        return default
    return float(value)


def _validate_fraction(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise BossCombatError(f"{name} must be in [0,1], got {value}")
