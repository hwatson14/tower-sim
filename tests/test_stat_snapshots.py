import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.engines.battle_conditions import BCRow, BattleConditions  # noqa: E402
from tower_sim.run.context import RunContext  # noqa: E402
from tower_sim.engines.stat_engine import StatEngine, StatInput  # noqa: E402
from tower_sim.registry.stat_registry import Phase, default_registry  # noqa: E402
from tower_sim.engines.stat_snapshots import build_at_wave_snapshot  # noqa: E402
from tower_sim.engines.tier_rules import TierRulesResult  # noqa: E402
from tower_sim.loaders.tier_battle_conditions import TierBattleCondition  # noqa: E402
from tower_sim.engines.wave_engine import RunWaveState  # noqa: E402


def test_build_at_wave_snapshot_applies_bc_then_heat() -> None:
    registry = default_registry()
    stat_inputs = [
        StatInput(stat_id="tower_hp", phase=Phase.START_OF_RUN, base_value=100.0),
        StatInput(stat_id="tower_regen", phase=Phase.START_OF_RUN, base_value=5.0),
        StatInput(stat_id="def_pct", phase=Phase.START_OF_RUN, base_value=0.1),
    ]
    engine_result = StatEngine(registry=registry).build(stat_inputs)
    battle_conditions = BattleConditions(
        [
            BCRow(
                tier="T1",
                context="farm",
                name="hp add",
                target="tower_hp",
                op="add",
                value=10.0,
                units="abs",
                priority=1,
            ),
            BCRow(
                tier="T1",
                context="farm",
                name="def mult",
                target="def_pct",
                op="mult",
                value=2.0,
                units="mult",
                priority=1,
            ),
        ]
    )
    wave_state = RunWaveState(W_actual=10, W_attack=8, W_health=9)
    heat_magnitudes = {"tower_hp": 999.0}

    snapshot = build_at_wave_snapshot(
        stat_inputs=stat_inputs,
        engine_result=engine_result,
        registry=registry,
        tier_rules=None,
        battle_conditions=battle_conditions,
        wave_state=wave_state,
        wave=10,
        run_context=RunContext.farming("T1"),
        heat_magnitudes=heat_magnitudes,
    )

    assert snapshot.frozen_order == registry.stat_ids_in_order()
    assert snapshot.values["wave_attack_index"] == 8.0
    assert snapshot.values["tower_hp"] == 999.0
    assert snapshot.applied_bc["tower_hp"] == 110.0
    assert snapshot.applied_heat["tower_hp"] == 999.0


def test_build_at_wave_snapshot_applies_tier_rules_before_bc_then_heat() -> None:
    registry = default_registry()
    stat_inputs = [
        StatInput(stat_id="eals_pct", phase=Phase.START_OF_RUN, base_value=0.2),
        StatInput(stat_id="ehls_pct", phase=Phase.START_OF_RUN, base_value=0.2),
        StatInput(stat_id="orb_damage_mult", phase=Phase.START_OF_RUN, base_value=1.0),
    ]
    engine_result = StatEngine(registry=registry).build(stat_inputs)

    tier_rules = TierRulesResult(
        tier=14,
        context=RunContext.farming("14"),
        conditions=[
            TierBattleCondition(
                tier=14,
                name="enemy_level_skip_reduction",
                kind="absolute_chance_subtract",
                value=0.05,
                unit="pp",
                notes="test",
            ),
            TierBattleCondition(
                tier=14,
                name="orb_resistance",
                kind="damage_multiplier",
                value=0.8,
                unit="mult",
                notes="test",
            ),
        ],
    )
    battle_conditions = BattleConditions(
        [
            BCRow(
                tier="14",
                context="farm",
                name="orb bc mult",
                target="orb_damage_mult",
                op="mult",
                value=0.5,
                units="mult",
                priority=1,
            )
        ]
    )

    snapshot = build_at_wave_snapshot(
        stat_inputs=stat_inputs,
        engine_result=engine_result,
        registry=registry,
        tier_rules=tier_rules,
        battle_conditions=battle_conditions,
        wave_state=RunWaveState(W_actual=10, W_attack=10, W_health=10),
        wave=10,
        run_context=RunContext.farming("14"),
        heat_magnitudes={"orb_damage_mult": 0.3},
    )

    assert snapshot.values["eals_pct"] == pytest.approx(0.15)
    assert snapshot.applied_bc["orb_damage_mult"] == pytest.approx(0.4)
    assert snapshot.applied_heat["orb_damage_mult"] == pytest.approx(0.3)
    assert snapshot.values["orb_damage_mult"] == pytest.approx(0.3)

