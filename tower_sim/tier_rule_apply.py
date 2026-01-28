from __future__ import annotations

from dataclasses import replace
from typing import Iterable, List

from tower_sim.stat_engine import StatInput
from tower_sim.tier_battle_conditions import TierBattleCondition
from tower_sim.tier_rules import TierRulesResult


SUPPORTED_BC = {
    ("enemy_level_skip_reduction", "absolute_chance_subtract", "pp"),
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


def _apply_skip_reduction(inputs_by_id: dict[str, StatInput], subtract_pp: float) -> None:
    for stat_id in ("eals_pct", "ehls_pct"):
        if stat_id not in inputs_by_id:
            raise ValueError(f"Missing StatInput for {stat_id} to apply tier rules.")
        current = inputs_by_id[stat_id]
        if current.tier_rule_delta is not None or current.tier_rule_multiplier is not None:
            raise ValueError(f"Tier rule already set for {stat_id}.")
        inputs_by_id[stat_id] = replace(current, tier_rule_delta=-subtract_pp)
