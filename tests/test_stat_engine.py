import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.engines.stat_engine import StatEngine, StatInput  # noqa: E402
from tower_sim.registry.stat_registry import Phase, UnknownStatError, default_registry  # noqa: E402
from tower_sim.engines.wave_engine import SkipRamp, make_wave_state  # noqa: E402


def test_stat_engine_composition_order() -> None:
    registry = default_registry()
    engine = StatEngine(registry=registry)
    inputs = [
        StatInput(
            stat_id="tower_hp",
            phase=Phase.START_OF_RUN,
            base_value=100,
            loadout_delta=20,
            enhancement_multiplier=1.1,
            tier_rule_delta=5,
            provenance="test",
        )
    ]
    result = engine.build(inputs)
    row = result.statbook.rows[0]
    assert row.final_value == "137.0"
    assert row.tier_rule_delta_or_multiplier == "delta:5"


def test_stat_engine_tier_multiplier() -> None:
    registry = default_registry()
    engine = StatEngine(registry=registry)
    inputs = [
        StatInput(
            stat_id="tower_hp",
            phase=Phase.START_OF_RUN,
            base_value=100,
            loadout_delta=0,
            enhancement_multiplier=1.2,
            tier_rule_multiplier=0.5,
            provenance="test",
        )
    ]
    result = engine.build(inputs)
    row = result.statbook.rows[0]
    assert row.final_value == "60.0"
    assert row.tier_rule_delta_or_multiplier == "mult:0.5"


def test_stat_engine_rejects_unknown_stat() -> None:
    registry = default_registry()
    engine = StatEngine(registry=registry)
    inputs = [
        StatInput(
            stat_id="unknown_stat",
            phase=Phase.START_OF_RUN,
            base_value=1,
        )
    ]
    with pytest.raises(UnknownStatError):
        engine.build(inputs)


def test_stat_engine_rejects_invalid_phase() -> None:
    registry = default_registry()
    engine = StatEngine(registry=registry)
    inputs = [
        StatInput(
            stat_id="tower_hp",
            phase=Phase.AT_WAVE,
            base_value=1,
        )
    ]
    with pytest.raises(ValueError):
        engine.build(inputs)


def test_stat_engine_derived_requires_exclusive_inputs() -> None:
    registry = default_registry()
    engine = StatEngine(registry=registry)
    inputs = [
        StatInput(
            stat_id="eals_pct",
            phase=Phase.START_OF_RUN,
            derived_value=0.1,
            base_value=1,
        )
    ]
    with pytest.raises(ValueError):
        engine.build(inputs)


def test_stat_engine_wave_state_derivation() -> None:
    registry = default_registry()
    engine = StatEngine(registry=registry)
    ramp = SkipRamp(start=0.0, end=1.0, ramp_waves=3)
    wave_state = make_wave_state(4, eals=ramp, ehls=ramp)

    result = engine.build([], wave_state=wave_state)

    assert wave_state.W_actual == 4
    assert wave_state.W_attack == 1
    assert wave_state.W_health == 1

    at_wave = result.run_stats[Phase.AT_WAVE].values
    assert at_wave["wave_attack_index"] == 1.0
    assert at_wave["wave_health_index"] == 1.0

    phases = {row.phase for row in result.statbook.rows}
    assert Phase.AT_WAVE.value in phases
