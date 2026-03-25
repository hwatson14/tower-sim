from engine.query_module_draw_policy import publish_module_draw_policy_surfaces
from compilers.module_reroll_spend_calculator import build_module_reroll_spend_calculator_from_qe
from compilers.module_shard_income_calculator import build_module_shard_income_calculator_from_drop_qe

def test_publish_module_draw_policy_surfaces():
    rows = {}
    publish_module_draw_policy_surfaces(rows)
    assert rows['derived::module.draw_policy.common_rate_pct'].final_value == 68.5
    assert rows['derived::module.draw_policy.rare_rate_pct'].final_value == 29.0
    assert rows['derived::module.draw_policy.epic_rate_pct'].final_value == 2.5
    assert rows['derived::module.draw_policy.epic_pity_draws'].final_value == 150.0
    assert rows['derived::module.draw_policy.ten_pull_minimum_rare'].final_value == 1.0

def test_reroll_spend_calculator_from_qe():
    out = build_module_reroll_spend_calculator_from_qe(lock_count=3, rolls=10)
    assert out['reroll_cost_per_roll'] == 500.0
    assert out['total_reroll_spend'] == 5000.0
    assert out['cost_exactness'] == 'exact_wiki_lock_ladder'

def test_shard_income_from_qe_includes_draw_lower_bound():
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
        'derived::module.shatter_policy.common_module_shards': 5,
        'derived::module.shatter_policy.rare_module_shards': 10,
    })
    assert out['gem_draw_shards_lower_bound_per_week'] > 0
    assert 'epic_draw_shard_equivalent_unresolved' in out['blocked_reasons']
