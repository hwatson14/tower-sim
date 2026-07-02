"""Equivalence engine tests for enemy health/damage pressure tables."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from evaluators.equivalence import (
    EnemyCurve,
    FixedSkipProfile,
    SurfaceCalibration,
    build_equivalence_table,
    displayed_wave_from_effective_wave,
    effective_wave_from_displayed_wave,
    equivalent_wave_for_budget,
    format_damage_value,
    integrate_effective_wave,
    parse_damage_label,
    pivot_displayed_waves,
)

pytestmark = pytest.mark.live


def test_damage_suffix_parser_uses_tower_order_after_n_d_aa_ab():
    assert parse_damage_label("100N") == pytest.approx(1e32)
    assert parse_damage_label("1D") == pytest.approx(1e33)
    assert parse_damage_label("40D") == pytest.approx(4e34)
    assert parse_damage_label("1aa") == pytest.approx(1e36)
    assert parse_damage_label("1ab") == pytest.approx(1e39)
    assert format_damage_value(4e34) == "40D"


def test_enemy_curve_solves_log_linearly_in_both_directions():
    curve = EnemyCurve(surface="Test", points=((100.0, 1e30), (200.0, 1e32)))

    assert curve.value_at_wave(150.0) == pytest.approx(1e31)
    assert curve.wave_for_value(1e31) == pytest.approx(150.0)


def test_fixed_skip_profile_keeps_ehls_and_eals_separate():
    profile = FixedSkipProfile(ehls=0.4488, eals=0.3596)

    assert effective_wave_from_displayed_wave(5000, profile.ehls) == pytest.approx(
        1 + 4999 * (1 - 0.4488)
    )
    assert effective_wave_from_displayed_wave(5000, profile.eals) == pytest.approx(
        1 + 4999 * (1 - 0.3596)
    )
    assert effective_wave_from_displayed_wave(5000, profile.ehls) < effective_wave_from_displayed_wave(
        5000, profile.eals
    )


def test_displayed_wave_inverse_for_fixed_skip_chance():
    effective = effective_wave_from_displayed_wave(5000, 0.4488)
    assert displayed_wave_from_effective_wave(effective, 0.4488) == pytest.approx(5000)


def test_integrated_effective_wave_supports_future_els_ramps():
    # Wave 1->3 increments: no skip, 50% skip, 50% skip.
    effective = integrate_effective_wave(4, lambda wave: 0.0 if wave == 1 else 0.5)
    assert effective == pytest.approx(1.0 + 1.0 + 0.5 + 0.5)


def test_equivalent_wave_for_budget_uses_ehls_on_health_axis():
    curve = EnemyCurve(surface="Tier 15", points=((2500.0, 1e32), (3000.0, 1e34)))

    result = equivalent_wave_for_budget(
        damage_label="1D",
        curve=curve,
        axis="health",
        skip_chance=0.4488,
    )

    assert result.raw_effective_wave == pytest.approx(2750.0)
    assert result.displayed_wave > result.raw_effective_wave
    assert result.skip_chance == pytest.approx(0.4488)


def test_surface_calibration_anchor_fits_only_target_surface():
    legend = EnemyCurve(surface="Legend", points=((500.0, 3.217e31), (750.0, 7.85e33)))
    calibration = SurfaceCalibration.from_anchor(
        surface="Legend",
        curve=legend,
        damage_label="40D",
        displayed_wave=550,
    )

    result = equivalent_wave_for_budget(
        damage_label="40D",
        curve=legend,
        axis="health",
        calibration=calibration,
    )

    assert result.displayed_wave == pytest.approx(550.0)
    assert result.budget_multiplier < 1.0


def test_build_table_pivots_displayed_waves():
    curves = {
        "Tier 14": EnemyCurve(surface="Tier 14", points=((100.0, 1e30), (200.0, 1e32))),
        "Tier 15": EnemyCurve(surface="Tier 15", points=((50.0, 1e30), (150.0, 1e32))),
    }

    rows = build_equivalence_table(
        damage_labels=("10N",),
        curves=curves,
        axis="health",
    )
    pivot = pivot_displayed_waves(rows)

    assert pivot == [{"damage_label": "10N", "Tier 14": 150, "Tier 15": 100}]


def test_enemy_curve_loads_surface_from_wide_csv(tmp_path: Path):
    path = tmp_path / "enemy-health-table.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["wave_actual", "Tier 14", "Tier 15"])
        writer.writerow([100, 1e30, 2e30])
        writer.writerow([200, 1e32, 2e32])

    curve = EnemyCurve.from_wide_csv(path, "Tier 15")

    assert curve.surface == "Tier 15"
    assert curve.wave_for_value(2e31) == pytest.approx(150.0)
