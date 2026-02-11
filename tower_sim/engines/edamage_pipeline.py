from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from tower_sim.loaders.table_paths import resolve_table_path
from typing import Dict, Iterable, Mapping, Sequence

from tower_sim.engines.edamage_formulas import (
    bullet_per_second,
    epd_aspd,
    epd_crit_chance,
    epd_critical,
)
from tower_sim.engines.stat_engine import StatInput
from tower_sim.loaders.card_masteries import load_card_masteries
from tower_sim.loaders.perk_tables import load_perk_definitions
from tower_sim.loaders.wiki.cards import get_card_effect
from tower_sim.loaders.wiki.perks import apply_standard_perk_bonus_multiplicative
from tower_sim.libs.labs_lib import load_labs_values
from tower_sim.registry.stat_registry import Phase


class EDamageInputError(ValueError):
    pass


@dataclass(frozen=True)
class ModuleSubstatSelection:
    slot: str
    substat: str
    rarity: str


@dataclass(frozen=True)
class CardConfig:
    damage_level: int | None = None
    attack_speed_level: int | None = None
    crit_chance_level: int | None = None
    attack_speed_mastery_level: int | None = None
    crit_chance_mastery_level: int | None = None


@dataclass(frozen=True)
class PerkConfig:
    picks: Mapping[str, int]
    standard_perk_bonus: float


@dataclass(frozen=True)
class EDamageInputs:
    base_damage: float
    base_crit_factor: float
    attack_speed_ws_level: float
    attack_speed_wsp_level: float
    attack_speed_lab_level: float
    crit_chance_ws_level: float
    damage_lab_level: float
    damage_ws_plus_multiplier: float
    relic_attack_speed_bonus: float
    relic_crit_chance_bonus: float
    vault_attack_speed_bonus: float
    vault_crit_chance_bonus: float
    card_config: CardConfig
    perk_config: PerkConfig
    module_substats: Sequence[ModuleSubstatSelection]
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
    attack_speed_substat = _sum_module_substats(inputs.module_substats, "Attack Speed")
    crit_chance_substat = _sum_module_substats(inputs.module_substats, "Crit Chance")
    crit_factor_substat = _sum_module_substats(inputs.module_substats, "Crit Factor")
    super_crit_chance_bonus = _sum_module_substats(
        inputs.module_substats, "Super Crit Chance"
    )
    super_crit_mult_bonus = _sum_module_substats(
        inputs.module_substats, "Super Crit Multi"
    )

    attack_speed_card_level = inputs.card_config.attack_speed_level or 0
    crit_chance_card_level = inputs.card_config.crit_chance_level or 0

    attack_speed = epd_aspd(
        ws_level=inputs.attack_speed_ws_level,
        wsp_level=inputs.attack_speed_wsp_level,
        lab_level=inputs.attack_speed_lab_level,
        has_card=inputs.card_config.attack_speed_level is not None,
        card_level=attack_speed_card_level,
        substat=attack_speed_substat,
        relic=inputs.relic_attack_speed_bonus,
        vault=inputs.vault_attack_speed_bonus,
        has_mastery=(inputs.card_config.attack_speed_mastery_level or 0) > 0,
        mastery_level=float(inputs.card_config.attack_speed_mastery_level or 0),
    )
    bullets = bullet_per_second(attack_speed)

    crit_chance = epd_crit_chance(
        ws_level=inputs.crit_chance_ws_level,
        has_card=inputs.card_config.crit_chance_level is not None,
        card_level=crit_chance_card_level,
        relic=inputs.relic_crit_chance_bonus,
        vault=inputs.vault_crit_chance_bonus,
        substat=crit_chance_substat,
        has_mastery=(inputs.card_config.crit_chance_mastery_level or 0) > 0,
        mastery_level=float(inputs.card_config.crit_chance_mastery_level or 0),
    )

    crit_factor = inputs.base_crit_factor + crit_factor_substat
    crit_multiplier = epd_critical(
        crit_chance=crit_chance,
        crit_factor=crit_factor,
        super_crit_chance=inputs.super_crit_chance + super_crit_chance_bonus,
        super_crit_mult=inputs.super_crit_mult + super_crit_mult_bonus,
        being_annihilator=inputs.being_annihilator_stacks,
    )

    damage_lab_multiplier = lookup_lab_multiplier(
        lab_name="Damage",
        level=int(inputs.damage_lab_level),
        neutral_value=1.0,
    )
    damage_card_multiplier = _resolve_card_multiplier(
        "Damage",
        inputs.card_config.damage_level,
        expected_unit="mult",
    )
    perk_multiplier = resolve_damage_perk_multiplier(inputs.perk_config)

    tower_damage = (
        inputs.base_damage
        * damage_lab_multiplier
        * inputs.damage_ws_plus_multiplier
        * damage_card_multiplier
        * perk_multiplier
    )
    tower_dps = tower_damage * crit_multiplier * bullets

    provenance = {
        "tower_damage": "tables/cache/wiki/cards_common.csv + tables/inputs/perks/perks_v1.csv + "
        "tables/inputs/economy/labs_values_v1.csv",
        "attack_speed": "tables/meta/registry/ep_formulas/mechanics_library.yaml (EPD_ASPD)",
        "crit_chance": "tables/meta/registry/ep_formulas/mechanics_library.yaml (EPD_CRIT_CHANCE)",
        "crit_multiplier": "tables/meta/registry/ep_formulas/mechanics_library.yaml (EPD_CRITICAL)",
        "tower_dps": "tables/meta/registry/ep_formulas/mechanics_library.yaml (BULLET_PER_SECOND)",
        "attack_speed": "mechanics/manifest.yaml -> active pack mechanics file (EPD_ASPD)",
        "crit_chance": "mechanics/manifest.yaml -> active pack mechanics file (EPD_CRIT_CHANCE)",
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


def lookup_lab_multiplier(
    lab_name: str,
    level: int,
    *,
    neutral_value: float = 1.0,
) -> float:
    if level <= 0:
        return neutral_value
    labs = load_labs_values()
    if lab_name not in labs:
        raise EDamageInputError(
            f"Missing lab {lab_name!r} in tables/inputs/economy/labs_values_v1.csv."
        )
    lab = labs[lab_name]
    if level not in lab.levels:
        raise EDamageInputError(
            f"Lab {lab_name!r} missing level {level} in tables/inputs/economy/labs_values_v1.csv."
        )
    value = lab.levels[level]
    if lab.unit == "percent_points":
        return 1.0 + (value / 100.0)
    if lab.unit == "percent":
        return 1.0 + value
    return float(value)


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


@dataclass(frozen=True)
class _ModuleSubstat:
    slot: str
    substat: str
    rarity: str
    value: float
    unit: str
    source: str


@lru_cache(maxsize=1)
def _module_substat_table() -> Dict[tuple[str, str, str], _ModuleSubstat]:
    table_path = resolve_table_path("module_substats")
    if not table_path.exists():
        raise FileNotFoundError(f"Missing module substat table: {table_path}")
    with table_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"slot", "substat", "rarity", "value", "unit", "source"}
        if reader.fieldnames is None:
            raise EDamageInputError(f"Missing header in {table_path}.")
        missing = required.difference(reader.fieldnames)
        if missing:
            raise EDamageInputError(
                f"Module substat table missing columns {sorted(missing)} in {table_path}."
            )
        parsed: Dict[tuple[str, str, str], _ModuleSubstat] = {}
        for row in reader:
            key = (row["slot"], row["substat"], row["rarity"])
            if key in parsed:
                raise EDamageInputError(f"Duplicate module substat entry {key}.")
            parsed[key] = _ModuleSubstat(
                slot=row["slot"],
                substat=row["substat"],
                rarity=row["rarity"],
                value=float(row["value"]),
                unit=row["unit"],
                source=row["source"],
            )
    if not parsed:
        raise EDamageInputError(f"Module substat table is empty: {table_path}.")
    return parsed


def _sum_module_substats(
    selections: Iterable[ModuleSubstatSelection],
    substat_name: str,
) -> float:
    total = 0.0
    table = _module_substat_table()
    for selection in selections:
        if selection.substat != substat_name:
            continue
        key = (selection.slot, selection.substat, selection.rarity)
        if key not in table:
            raise EDamageInputError(
                f"Missing module substat {key} in tables/inputs/modules/module_substats_v1.csv."
            )
        entry = table[key]
        total += _coerce_substat_value(entry.value, entry.unit)
    return total


def _coerce_substat_value(value: float, unit: str) -> float:
    if unit == "percent":
        return value / 100.0
    if unit in {"flat", "mult", "sec", "count"}:
        return value
    raise EDamageInputError(f"Unsupported module substat unit {unit!r}.")


def _resolve_card_multiplier(
    card_name: str,
    level: int | None,
    *,
    expected_unit: str,
) -> float:
    if level is None:
        return 1.0
    effect = get_card_effect(card_name, level)
    if effect.unit != expected_unit:
        raise EDamageInputError(
            f"Card {card_name!r} expected unit {expected_unit!r}, got {effect.unit!r}."
        )
    return effect.value


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
    "CardConfig",
    "EDamageInputs",
    "EDamageInputError",
    "EDamageOutputs",
    "ModuleSubstatSelection",
    "PerkConfig",
    "build_edamage_stat_inputs",
    "compute_edamage_outputs",
    "lookup_lab_multiplier",
    "resolve_damage_perk_multiplier",
    "resolve_card_mastery_value",
]
