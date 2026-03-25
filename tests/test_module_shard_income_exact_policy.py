from compilers.module_shard_income_calculator import build_module_shard_income_calculator_from_drop_qe

def test_shard_income_exact_under_package_draw_policy():
    out = build_module_shard_income_calculator_from_drop_qe({
        'derived::runtime.eligible_bosses_per_run': 100,
        'derived::runtime.hours_per_run': 2.5,
        'derived::module.runtime_profile.farming_hours_per_day': 23.5,
        'planner.manual_policy.module.missions_per_week': 14,
        'derived::module.mission_policy.total_daily_mission_shards': 49,
        'derived::module.drop_policy.expected_shatter_equivalent_shards_per_boss': 0.165,
        'derived::module.resource_policy.gems_allocated_to_modules_per_week': 700,
        'derived::module.draw_policy.gem_cost_per_draw': 20,
        'derived::module.draw_policy.common_rate_pct': 68.5,
        'derived::module.draw_policy.rare_rate_pct': 29.0,
        'derived::module.draw_policy.epic_rate_pct': 2.5,
        'derived::module.shatter_policy.common_module_shards': 7.0,
        'derived::module.shatter_policy.rare_module_shards': 14.0,
        'derived::module.draw_policy.epic_draw_immediate_shard_value': 0.0,
        'derived::module.draw_policy.ten_pull_ev_multiplier': 1.0,
    })
    assert out['income_exactness'] == 'exact_under_package_draw_policy'
    assert out['blocked_reasons'] == []
    assert out['expected_shards_per_draw'] > 0
