from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from typing import Dict, Mapping

from tower_sim.engines.edamage_formulas import (
    bullet_per_second,
    epd_critical,
)
from tower_sim.engines.stat_engine import StatInput
from tower_sim.loaders.card_masteries import load_card_masteries
from tower_sim.loaders.perk_tables import load_perk_definitions
from tower_sim.loaders.wiki.perks import apply_standard_perk_bonus_multiplicative
from tower_sim.registry.stat_registry import Phase


class EDamageInputError(ValueError):
    pass


@dataclass(frozen=True)
class PerkConfig:
    picks: Mapping[str, int]
    standard_perk_bonus: float


@dataclass(frozen=True)
class EDamageInputs:
    tower_damage: float
    tower_attack_speed: float
    tower_crit_chance: float
    tower_crit_factor: float
    being_annihilator_stacks: float
    super_crit_chance: float
    super_crit_mult: float


@dataclass(frozen=True)
class EDamageOutputs:
    tower_damage: float
    attack_speed: float
    crit_chance: float
    crit_multiplier: float
    bullets_per_second: float
    tower_dps: float
    provenance: Mapping[str, str]


def build_edamage_stat_inputs(
    inputs: EDamageInputs,
    *,
    phase: Phase = Phase.START_OF_RUN,
) -> list[StatInput]:
    outputs = compute_edamage_outputs(inputs)
    return [
        StatInput(
            stat_id="tower_damage",
            phase=phase,
            derived_value=outputs.tower_damage,
            provenance=outputs.provenance.get("tower_damage"),
        ),
        StatInput(
            stat_id="tower_attack_speed",
            phase=phase,
            derived_value=outputs.attack_speed,
            provenance=outputs.provenance.get("attack_speed"),
        ),
        StatInput(
            stat_id="tower_crit_chance",
            phase=phase,
            derived_value=outputs.crit_chance,
            provenance=outputs.provenance.get("crit_chance"),
        ),
        StatInput(
            stat_id="tower_crit_multiplier",
            phase=phase,
            derived_value=outputs.crit_multiplier,
            provenance=outputs.provenance.get("crit_multiplier"),
        ),
        StatInput(
            stat_id="tower_dps",
            phase=phase,
            derived_value=outputs.tower_dps,
            provenance=outputs.provenance.get("tower_dps"),
        ),
    ]


def compute_edamage_outputs(inputs: EDamageInputs) -> EDamageOutputs:
    attack_speed = inputs.tower_attack_speed
    bullets = bullet_per_second(attack_speed)
    crit_chance = inputs.tower_crit_chance
    crit_factor = inputs.tower_crit_factor
    crit_multiplier = epd_critical(
        crit_chance=crit_chance,
        crit_factor=crit_factor,
        super_crit_chance=inputs.super_crit_chance,
        super_crit_mult=inputs.super_crit_mult,
        being_annihilator=inputs.being_annihilator_stacks,
    )
    tower_damage = inputs.tower_damage
    tower_dps = tower_damage * crit_multiplier * bullets

    provenance = {
        "tower_damage": "stat_input_compiler:canonical_start_of_run:tower_damage",
        "attack_speed": "stat_input_compiler:canonical_start_of_run:tower_attack_speed",
        "crit_chance": "stat_input_compiler:canonical_start_of_run:tower_crit_chance",
        "crit_multiplier": "mechanics/manifest.yaml -> active pack mechanics file (EPD_CRITICAL)",
        "tower_dps": "mechanics/manifest.yaml -> active pack mechanics file (BULLET_PER_SECOND)",
    }
    return EDamageOutputs(
        tower_damage=tower_damage,
        attack_speed=attack_speed,
        crit_chance=crit_chance,
        crit_multiplier=crit_multiplier,
        bullets_per_second=bullets,
        tower_dps=tower_dps,
        provenance=provenance,
    )


def resolve_damage_perk_multiplier(config: PerkConfig) -> float:
    definitions = _perk_definitions_by_name()
    multiplier = 1.0
    for perk_name, picks in config.picks.items():
        if picks <= 0:
            continue
        if perk_name not in definitions:
            raise EDamageInputError(f"Unknown perk {perk_name!r} in tables/inputs/perks/perks_v1.csv.")
        definition = definitions[perk_name]
        perk_multiplier = _parse_damage_multiplier(definition.effect)
        if perk_multiplier is None:
            raise EDamageInputError(
                f"Perk {perk_name!r} missing damage multiplier in {definition.effect!r}."
            )
        if definition.category == "standard":
            perk_base = perk_multiplier - 1.0
            multiplier *= apply_standard_perk_bonus_multiplicative(
                perk_base, picks, config.standard_perk_bonus
            )
        else:
            if picks != 1:
                raise EDamageInputError(
                    f"Perk {perk_name!r} expects one pick, got {picks}."
                )
            multiplier *= perk_multiplier
    return multiplier


def _parse_damage_multiplier(effect: str) -> float | None:
    raw = effect.replace("×", "x").replace("−", "-")
    match = re.search(r"x\s*([0-9]+(?:\.[0-9]+)?)", raw)
    if match:
        return float(match.group(1))
    match = re.search(r"Tower Damage\\s*[-+]?([0-9]+(?:\\.[0-9]+)?)%", raw)
    if match:
        return 1.0 - (float(match.group(1)) / 100.0)
    return None


@dataclass(frozen=True)
class _PerkDefinition:
    perk_name: str
    category: str
    effect: str


@lru_cache(maxsize=1)
def _perk_definitions_by_name() -> Dict[str, _PerkDefinition]:
    definitions = load_perk_definitions()
    return {
        definition.perk_name: _PerkDefinition(
            perk_name=definition.perk_name,
            category=definition.category,
            effect=definition.effect,
        )
        for definition in definitions
    }


def inputs_from_canonical_values(values: Mapping[str, float]) -> EDamageInputs:
    required = (
        "tower_damage",
        "tower_attack_speed",
        "tower_crit_chance",
        "tower_crit_multiplier",
        "super_crit_chance",
        "super_crit_mult",
    )
    missing = [stat_id for stat_id in required if stat_id not in values]
    if missing:
        raise EDamageInputError(
            "Missing canonical edamage stat values: " + ", ".join(sorted(missing))
        )
    return EDamageInputs(
        tower_damage=float(values["tower_damage"]),
        tower_attack_speed=float(values["tower_attack_speed"]),
        tower_crit_chance=float(values["tower_crit_chance"]),
        tower_crit_factor=float(values["tower_crit_multiplier"]),
        super_crit_chance=float(values["super_crit_chance"]),
        super_crit_mult=float(values["super_crit_mult"]),
        being_annihilator_stacks=0.0,
    )


def resolve_card_mastery_value(card_name: str, level: int | None) -> float:
    if level is None or level <= 0:
        return 0.0
    masteries = load_card_masteries()
    if card_name not in masteries:
        raise EDamageInputError(
            f"Missing card mastery {card_name!r} in tables/inputs/cards/card_masteries_v1.csv."
        )
    row = masteries[card_name]
    if level > len(row.level_values):
        raise EDamageInputError(
            f"Card mastery {card_name!r} level {level} out of range."
        )
    raw = row.level_values[level - 1].strip().lower().replace("x", "")
    if raw.endswith("%"):
        return float(raw[:-1]) / 100.0
    return float(raw)


__all__ = [
    "EDamageInputs",
    "EDamageInputError",
    "EDamageOutputs",
    "PerkConfig",
    "build_edamage_stat_inputs",
    "compute_edamage_outputs",
    "inputs_from_canonical_values",
    "resolve_damage_perk_multiplier",
    "resolve_card_mastery_value",
]
