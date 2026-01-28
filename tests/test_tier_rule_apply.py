import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.run_context import RunContext  # noqa: E402
from tower_sim.stat_engine import StatInput  # noqa: E402
from tower_sim.stat_registry import Phase  # noqa: E402
from tower_sim.tier_battle_conditions import TierBattleCondition  # noqa: E402
from tower_sim.tier_rule_apply import apply_tier_rules_to_inputs  # noqa: E402
from tower_sim.tier_rules import TierRulesResult  # noqa: E402


def _base_inputs() -> list[StatInput]:
    return [
        StatInput(stat_id="eals_pct", phase=Phase.START_OF_RUN, base_value=0.2),
        StatInput(stat_id="ehls_pct", phase=Phase.START_OF_RUN, base_value=0.3),
        StatInput(stat_id="orb_damage_mult", phase=Phase.START_OF_RUN, base_value=1.0),
    ]


def test_apply_skip_reduction_sets_tier_rule_delta() -> None:
    context = RunContext.from_mode("tier")
    condition = TierBattleCondition(
        tier=14,
        name="enemy_level_skip_reduction",
        kind="absolute_chance_subtract",
        value=0.025,
        unit="pp",
        notes="",
    )
    tier_rules = TierRulesResult(tier=14, context=context, conditions=[condition])

    inputs = apply_tier_rules_to_inputs(_base_inputs(), tier_rules)

    eals = next(item for item in inputs if item.stat_id == "eals_pct")
    ehls = next(item for item in inputs if item.stat_id == "ehls_pct")

    assert eals.tier_rule_delta == -0.025
    assert ehls.tier_rule_delta == -0.025


def test_apply_damage_multiplier_sets_tier_rule_multiplier() -> None:
    context = RunContext.from_mode("tier")
    condition = TierBattleCondition(
        tier=14,
        name="orb_resistance",
        kind="damage_multiplier",
        value=0.5,
        unit="mult",
        notes="",
    )
    tier_rules = TierRulesResult(tier=14, context=context, conditions=[condition])

    inputs = apply_tier_rules_to_inputs(_base_inputs(), tier_rules)

    orb = next(item for item in inputs if item.stat_id == "orb_damage_mult")
    assert orb.tier_rule_multiplier == 0.5


def test_apply_unknown_condition_raises() -> None:
    context = RunContext.from_mode("tier")
    condition = TierBattleCondition(
        tier=14,
        name="vampire_ultimate",
        kind="drain_speed_bonus",
        value=0.5,
        unit="mult_over_base",
        notes="",
    )
    tier_rules = TierRulesResult(tier=14, context=context, conditions=[condition])

    inputs = _base_inputs()
    with pytest.raises(ValueError, match="Unsupported"):
        apply_tier_rules_to_inputs(inputs, tier_rules)
