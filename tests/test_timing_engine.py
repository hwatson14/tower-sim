from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.timing_engine import (
    TimingMechanic,
    TimingSurfaces,
    average_active_fraction_over_interval,
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
