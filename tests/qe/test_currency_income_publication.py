from __future__ import annotations

import pytest

from qe.models import StatRow
from qe.query_currency_income import publish_currency_income_surfaces

pytestmark = pytest.mark.live


def _row(value: float, *, value_type: str = "scalar", unit: str = "unit") -> StatRow:
    return StatRow(
        stat_name="fixture",
        final_value=value,
        value_type=value_type,
        source_count=1,
        status="resolved",
        contributors=[{"value": value, "unit": unit}],
        schema={"unit": unit},
    )


def test_publish_currency_income_surfaces__publishes_deterministic_shards_from_runtime_and_module_surfaces():
    rows = {
        "support_surface::scenario.bosses_per_day_effective": _row(100.0, unit="bosses_per_day"),
        "derived::module.drop_policy.expected_shatter_equivalent_shards_per_boss": _row(2.5, unit="shards_per_boss"),
        "planner.manual_policy.module.missions_per_week": _row(7.0, value_type="per_week", unit="missions_per_week"),
        "derived::module.mission_policy.total_daily_mission_shards": _row(8.0, unit="shards_per_mission"),
    }

    publish_currency_income_surfaces(rows)

    assert rows["derived::economy.income.shards"].final_value == pytest.approx(1806.0)


def test_publish_currency_income_surfaces__uses_exact_package_draw_ev_when_promoted_surfaces_exist():
    rows = {
        "support_surface::scenario.bosses_per_day_effective": _row(0.0, unit="bosses_per_day"),
        "derived::module.drop_policy.expected_shatter_equivalent_shards_per_boss": _row(0.0, unit="shards_per_boss"),
        "derived::module.resource_policy.gems_allocated_to_modules_per_week": _row(200.0, value_type="per_week", unit="gems_per_week"),
        "derived::module.draw_policy.gem_cost_per_draw": _row(20.0, unit="gems"),
        "derived::module.draw_policy.common_rate_pct": _row(68.5, unit="pct"),
        "derived::module.draw_policy.rare_rate_pct": _row(29.0, unit="pct"),
        "derived::module.draw_policy.epic_rate_pct": _row(2.5, unit="pct"),
        "derived::module.shatter_policy.common_module_shards": _row(5.0, unit="shards"),
        "derived::module.shatter_policy.rare_module_shards": _row(10.0, unit="shards"),
        "derived::module.draw_policy.epic_draw_immediate_shard_value": _row(0.0, unit="shards"),
        "derived::module.draw_policy.ten_pull_ev_multiplier": _row(1.0, unit="multiplier"),
    }

    publish_currency_income_surfaces(rows)

    assert rows["derived::economy.income.shards"].final_value == pytest.approx(63.25)
