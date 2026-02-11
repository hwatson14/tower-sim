import sys
from pathlib import Path


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.run.context import RunContext  # noqa: E402
from tower_sim.engines.stat_engine import StatEngine, StatInput  # noqa: E402
from tower_sim.registry.stat_registry import Phase, default_registry  # noqa: E402
from tower_sim.loaders.tier_battle_conditions import TierBattleCondition  # noqa: E402
from tower_sim.engines.tier_rules import TierRulesResult  # noqa: E402


def test_build_with_tier_rules_applies_skip_reduction() -> None:
    registry = default_registry()
    engine = StatEngine(registry)
    inputs = [
        StatInput(stat_id="eals_pct", phase=Phase.START_OF_RUN, base_value=0.2),
        StatInput(stat_id="ehls_pct", phase=Phase.START_OF_RUN, base_value=0.3),
        StatInput(stat_id="orb_damage_mult", phase=Phase.START_OF_RUN, base_value=1.0),
    ]
    condition = TierBattleCondition(
        tier=14,
        name="enemy_level_skip_reduction",
        kind="absolute_chance_subtract",
        value=0.025,
        unit="pp",
        notes="",
    )
    tier_rules = TierRulesResult(
        tier=14,
        context=RunContext.from_mode("tier"),
        conditions=[condition],
    )

    result = engine.build_with_tier_rules(inputs, tier_rules)

    eals_row = next(row for row in result.statbook.rows if row.stat_id == "eals_pct")
    assert str(eals_row.tier_rule_delta_or_multiplier) == "-0.025"
