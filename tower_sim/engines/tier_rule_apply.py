from __future__ import annotations

from dataclasses import replace
from typing import Iterable, List, TYPE_CHECKING
from tower_sim.loaders.tier_battle_conditions import TierBattleCondition
from tower_sim.engines.tier_rules import TierRulesResult

if TYPE_CHECKING:
    from tower_sim.engines.stat_engine import StatInput


SUPPORTED_BC = {
    ("enemy_level_skip_reduction", "absolute_chance_subtract", "pp"),
    ("more_bosses", "boss_interval_waves", "waves"),
    ("orb_resistance", "damage_multiplier", "mult"),
    ("death_ray_resistance", "damage_multiplier", "mult"),
    ("thorns_resistance", "damage_multiplier", "mult"),
    ("plasma_cannon_resistance", "damage_multiplier", "mult"),
    ("knockback_resistance", "knockback_multiplier", "mult"),
}


def apply_tier_rules_to_inputs(
    inputs: Iterable[StatInput],
    tier_rules: TierRulesResult,
) -> List[StatInput]:
    inputs_by_id = {item.stat_id: item for item in inputs}
    for condition in tier_rules.conditions:
        _apply_condition(inputs_by_id, condition)
    return list(inputs_by_id.values())


def _apply_condition(
    inputs_by_id: dict[str, StatInput],
    condition: TierBattleCondition,
) -> None:
    key = (condition.name, condition.kind, condition.unit)
    if key not in SUPPORTED_BC:
        raise ValueError(
            "Unsupported tier battle condition: "
            f"{condition.name}/{condition.kind}/{condition.unit}"
        )
    if condition.value < 0:
        raise ValueError(
            f"Tier battle condition value must be non-negative: {condition.value}"
        )
    if condition.name == "enemy_level_skip_reduction":
        _apply_skip_reduction(inputs_by_id, condition.value)
        return
    if condition.name == "more_bosses":
        # Provenance: tables/tier_battle_conditions.csv.
        # Current MAX_WAVE model resolves boss survivability per-wave and does not
        # model spawn cadence yet, so this BC is accepted as a no-op for v1.
        return
    if condition.name == "orb_resistance":
        _apply_multiplier(inputs_by_id, "orb_damage_mult", condition.value)
        return
    if condition.name == "death_ray_resistance":
        _apply_multiplier(inputs_by_id, "death_ray_damage_mult", condition.value)
        return
    if condition.name == "thorns_resistance":
        _apply_multiplier(inputs_by_id, "thorns_damage_mult", condition.value)
        return
    if condition.name == "plasma_cannon_resistance":
        _apply_multiplier(inputs_by_id, "plasma_cannon_damage_mult", condition.value)
        return
    if condition.name == "knockback_resistance":
        _apply_multiplier(inputs_by_id, "knockback_mult", condition.value)
        return


def _apply_skip_reduction(inputs_by_id: dict[str, StatInput], subtract_pp: float) -> None:
    for stat_id in ("eals_pct", "ehls_pct"):
        if stat_id not in inputs_by_id:
            raise ValueError(f"Missing StatInput for {stat_id} to apply tier rules.")
        current = inputs_by_id[stat_id]
        if current.tier_rule_delta is not None or current.tier_rule_multiplier is not None:
            raise ValueError(f"Tier rule already set for {stat_id}.")
        inputs_by_id[stat_id] = replace(current, tier_rule_delta=-subtract_pp)


def _apply_multiplier(
    inputs_by_id: dict[str, StatInput], stat_id: str, multiplier: float
) -> None:
    if stat_id not in inputs_by_id:
        raise ValueError(f"Missing StatInput for {stat_id} to apply tier rules.")
    current = inputs_by_id[stat_id]
    if current.tier_rule_delta is not None or current.tier_rule_multiplier is not None:
        raise ValueError(f"Tier rule already set for {stat_id}.")
    inputs_by_id[stat_id] = replace(current, tier_rule_multiplier=multiplier)
