from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.engines.uptime import (
    TimedEffect,
    aggregate_uptime,
    build_bot_effects,
    build_gcomp_activation_intervals,
    build_periodic_activation_intervals,
    overlap_fraction,
)
from tower_sim.engines.wave_time import active_preset_name, wa_reduction_from_snapshot
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids


def _snapshot():
    return compile_account_snapshot(parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv")))


def test_wa_reduction_from_snapshot_not_equipped_tourney() -> None:
    snap = _snapshot()
    assert wa_reduction_from_snapshot(snapshot=snap, run_type="tournament") == 0.0


def test_wa_reduction_from_snapshot_equipped_farming() -> None:
    snap = _snapshot()
    assert wa_reduction_from_snapshot(snapshot=snap, run_type="farming") == 0.54




def test_active_preset_name_accepts_enum_like_mode() -> None:
    class _Mode:
        value = "farming"

    snap = _snapshot()
    assert active_preset_name(run_type=_Mode(), snapshot=snap) == "Farming"

def test_periodic_uptime_fraction_matches_duration_over_cooldown() -> None:
    intervals = build_periodic_activation_intervals(duration_s=2.0, cooldown_s=10.0, window_s=100.0)
    effect = TimedEffect(name="E", activation_intervals=intervals, coin_multiplier=2.0)
    summary = aggregate_uptime([effect], window_s=100.0)
    assert summary.state_fractions[("E",)] == pytest.approx(0.2)


def test_gcomp_package_event_triggers_earlier_than_base_cooldown() -> None:
    base = build_periodic_activation_intervals(
        duration_s=5.0,
        cooldown_s=30.0,
        window_s=60.0,
        phase_s=30.0,
    )
    gcomp = build_gcomp_activation_intervals(
        base_cooldown_s=30.0,
        duration_s=5.0,
        package_event_times_s=[10.0],
        seconds_reduced_per_package=25.0,
        window_s=60.0,
    )
    assert base[0][0] == 30.0
    assert gcomp[0][0] < 30.0
    assert gcomp[0][0] > 0.0


def test_overlap_fraction_toy_case() -> None:
    left = ((0.0, 5.0), (10.0, 15.0))
    right = ((3.0, 8.0), (12.0, 14.0))
    frac = overlap_fraction(left, right, window_s=20.0)
    assert frac == 0.2


def test_bot_effects_are_table_backed() -> None:
    effects = build_bot_effects(
        bot_levels={
            "Flame Bot": {"Damage R.": 1, "Cooldown": 1},
            "Golden Bot": {"Bonus": 1, "Duration": 1, "Cooldown": 1},
            "Amplify Bot": {"Bonus": 1, "Duration": 1, "Cooldown": 1},
        },
        window_s=120.0,
    )
    by_name = {effect.name: effect for effect in effects}
    assert "Flame Bot" not in by_name
    assert by_name["Golden Bot"].coin_multiplier == 2.2
    assert by_name["Amplify Bot"].damage_multiplier == 3.9


def test_bot_effects_use_bot_specific_intervals() -> None:
    effects = build_bot_effects(
        bot_levels={
            "Golden Bot": {"Bonus": 1, "Duration": 1, "Cooldown": 1},
        },
        window_s=300.0,
    )
    golden = {e.name: e for e in effects}["Golden Bot"]
    assert len(golden.activation_intervals) > 0
    assert golden.activation_intervals[0][1] == pytest.approx(20.5)

