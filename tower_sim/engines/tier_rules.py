from __future__ import annotations

from dataclasses import dataclass
from typing import List

from tower_sim.run.context import RunContext
from tower_sim.loaders.tier_battle_conditions import TierBattleCondition, TierBattleConditions


# User-provided clarification: tiers 1–13 have no battle conditions.
NO_BATTLE_CONDITION_TIERS = set(range(1, 14))


@dataclass(frozen=True)
class TierRulesResult:
    tier: int
    context: RunContext
    conditions: List[TierBattleCondition]


def build_tier_rules(
    tier: int,
    context: RunContext,
    catalog: TierBattleConditions,
) -> TierRulesResult:
    conditions = catalog.for_tier(tier)
    if not conditions:
        if tier in NO_BATTLE_CONDITION_TIERS:
            return TierRulesResult(tier=tier, context=context, conditions=[])
        raise ValueError(f"No tier battle conditions found for tier {tier}.")
    return TierRulesResult(tier=tier, context=context, conditions=conditions)
