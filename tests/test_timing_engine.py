from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.timing_engine import (
    TimingMechanic,
    TimingSurfaces,
    average_active_fraction_over_interval,
    build_default_econ_timing_mechanics,
    compute_average_combined_multiplier,
    compute_average_damage_reduction_fraction_over_interval,
    overlap_fraction,
)


def test_overlap_fraction_perfect_sync():
    a = TimingMechanic("a", active_duration_s=10.0, cooldown_s=10.0)
    b = TimingMechanic("b", active_duration_s=10.0, cooldown_s=10.0)
    assert abs(overlap_fraction(a, b) - 0.5) < 1e-9


def test_overlap_fraction_anti_sync():
    a = TimingMechanic("a", active_duration_s=10.0, cooldown_s=10.0, phase_offset_s=0.0)
    b = TimingMechanic("b", active_duration_s=10.0, cooldown_s=10.0, phase_offset_s=10.0)
    assert overlap_fraction(a, b) == 0.0


def test_average_combined_multiplier_matches_manual_segments():
    a = TimingMechanic("a", active_duration_s=10.0, cooldown_s=10.0, active_multiplier=2.0)
    b = TimingMechanic("b", active_duration_s=10.0, cooldown_s=10.0, phase_offset_s=10.0, active_multiplier=3.0)
    # Over one 20s cycle: 10s at x2, 10s at x3. Average = 2.5
    assert abs(compute_average_combined_multiplier([a, b]) - 2.5) < 1e-9


def test_average_active_fraction_over_interval_partial_window():
    mechanic = TimingMechanic("cf", active_duration_s=20.0, cooldown_s=20.0)
    assert abs(average_active_fraction_over_interval(mechanic, 10.0, 30.0) - 0.5) < 1e-9


def test_compute_average_damage_reduction_fraction_over_interval_cf_only():
    timing = TimingSurfaces(
        cf_effective_duration_s=20.0,
        cf_effective_cooldown_s=20.0,
        cf_damage_reduction_pct=30.0,
    )
    assert abs(compute_average_damage_reduction_fraction_over_interval(timing, 10.0, 30.0) - 0.15) < 1e-9


def test_build_default_econ_timing_mechanics_uses_direct_multipliers():
    """Regression: active_multiplier must be the direct xN surface value, not 1+bonus."""
    rows = {
        "mechanic_param::uw.golden_tower.duration_seconds": {"final_value": 42.0},
        "mechanic_param::uw.golden_tower.cooldown_seconds": {"final_value": 180.0},
        "mechanic_param::uw.golden_tower.bonus_multiplier": {"final_value": 26.85},
        "mechanic_param::uw.black_hole.duration_seconds": {"final_value": 38.0},
        "runtime_mechanic_param::uw.black_hole.duration_seconds": {"final_value": 10.0},
        "mechanic_param::uw.black_hole.cooldown_seconds": {"final_value": 46.0},
        "runtime_mechanic_param::uw.black_hole.cooldown_seconds": {"final_value": 0.0},
        "runtime_mechanic_param::uw.black_hole.coin_bonus_multiplier": {"final_value": 11.0},
        "mechanic_param::bot.golden.duration_seconds": {"final_value": 32.0},
        "mechanic_param::bot.golden.cooldown_seconds": {"final_value": 90.0},
        "mechanic_param::bot.golden.bonus_multiplier": {"final_value": 6.4},
    }
    mechanics = {m.mechanic_id: m for m in build_default_econ_timing_mechanics(rows)}
    assert abs(mechanics["golden_tower"].active_multiplier - 26.85) < 1e-6
    assert abs(mechanics["black_hole_coin"].active_multiplier - 11.0) < 1e-9
    assert abs(mechanics["golden_bot"].active_multiplier - 6.4) < 1e-9
