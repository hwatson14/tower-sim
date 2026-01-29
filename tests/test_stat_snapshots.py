import sys
from pathlib import Path


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.battle_conditions import BCRow, BattleConditions  # noqa: E402
from tower_sim.run_context import RunContext  # noqa: E402
from tower_sim.stat_engine import StatEngine, StatInput  # noqa: E402
from tower_sim.stat_registry import Phase, default_registry  # noqa: E402
from tower_sim.stat_snapshots import build_at_wave_snapshot  # noqa: E402
from tower_sim.wave_engine import RunWaveState  # noqa: E402


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
