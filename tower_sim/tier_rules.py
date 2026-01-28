from __future__ import annotations

from dataclasses import dataclass
from typing import List

from tower_sim.run_context import RunContext
from tower_sim.tier_battle_conditions import TierBattleCondition, TierBattleConditions


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
        raise ValueError(f"No tier battle conditions found for tier {tier}.")
    return TierRulesResult(tier=tier, context=context, conditions=conditions)
