from __future__ import annotations

import pytest

from evaluators.tournament_power import (
    ChronoFieldControl,
    InnerLandMineControl,
    chrono_field_effective_duration_seconds,
    chrono_field_exposure_factor,
    chrono_field_uptime,
    inner_land_mine_effective_quantity,
    inner_land_mine_generation_per_second,
)
from simulators.horizon_progression import (
    module_shards_after_days,
    piecewise_income,
    unlock_day,
)


def test_stone_unlock_day_from_zero_balance():
    assert unlock_day(1653, income_per_day=733 / 7) == pytest.approx(15.7858117326)


def test_piecewise_income_applies_multiplier_only_after_breakpoint():
    value = piecewise_income(
        56,
        base_income_per_day=20.6565,
        multiplier=1.133,
        multiplier_start_day=15.7858117326,
    )
    assert value == pytest.approx(1267.2450225)


def test_module_shards_are_continuous_resource_flow():
    assert module_shards_after_days(
        56,
        starting_shards=326_275,
        shards_per_day=1_749,
    ) == pytest.approx(424_219)


def test_uwd_cf_duration_pair_repairs_most_of_condition_loss():
    control = ChronoFieldControl(
        base_duration_seconds=50,
        cooldown_seconds=60,
        speed_reduction=0.90,
        uwd_duration_penalty_seconds=10,
        primary_duration_bonus_seconds=10,
        assist_duration_bonus_seconds=10,
        assist_substat_efficiency=0.34,
    )
    assert chrono_field_effective_duration_seconds(control) == pytest.approx(53.4)
    assert chrono_field_uptime(control) == pytest.approx(0.89)
    assert chrono_field_exposure_factor(control) == pytest.approx(5.0251256281)


def test_uwd_ilm_pair_keeps_full_mine_quantity_but_lower_cf_exposure():
    cf_control = ChronoFieldControl(
        base_duration_seconds=50,
        cooldown_seconds=60,
        speed_reduction=0.90,
        uwd_duration_penalty_seconds=10,
    )
    ilm_control = InnerLandMineControl(
        base_quantity=5,
        cooldown_seconds=160,
        stun_seconds=2.5,
        primary_quantity_bonus=3,
        assist_quantity_bonus=3,
        assist_substat_efficiency=0.34,
    )

    assert chrono_field_exposure_factor(cf_control) == pytest.approx(2.5)
    assert inner_land_mine_effective_quantity(ilm_control) == pytest.approx(9.02)
    assert inner_land_mine_generation_per_second(ilm_control) == pytest.approx(0.056375)
