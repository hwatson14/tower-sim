from engine.query_module_drop_economy import publish_module_drop_economy_surfaces
from compilers.module_reroll_income_calculator import build_module_reroll_income_calculator_from_drop_qe
from compilers.module_shard_income_calculator import build_module_shard_income_calculator_from_drop_qe

def test_publish_module_drop_economy_surfaces(tmp_path):
    path = tmp_path / 'manual_advisory_inputs.json'
    path.write_text('{"inputs":[{"input_id":"module.runtime.tier_for_drop_tables","value":12,"is_set":true},{"input_id":"module.labs.reroll_shards_bonus","value":5,"is_set":true},{"input_id":"module.labs.common_drop_chance_bonus_pct","value":0.3,"is_set":true},{"input_id":"module.labs.rare_drop_chance_bonus_pct","value":0.2,"is_set":true},{"input_id":"module.labs.daily_mission_shards_bonus","value":7,"is_set":true}]}')
    rows = {}
    publish_module_drop_economy_surfaces(rows, manual_input_path=path)
    assert rows['derived::module.drop_policy.reroll_shards_per_boss'].final_value == 50.0
    assert rows['derived::module.drop_policy.common_module_drop_chance_pct'].final_value == 2.3
    assert rows['derived::module.mission_policy.daily_mission_shards_bonus'].final_value == 7.0

def test_reroll_income_from_drop_qe():
    out = build_module_reroll_income_calculator_from_drop_qe({
        'derived::runtime.eligible_bosses_per_run': 100,
        'derived::runtime.hours_per_run': 2.5,
        'derived::module.runtime_profile.farming_hours_per_day': 23.5,
        'derived::module.drop_policy.reroll_shard_drop_chance_pct': 15.0,
        'derived::module.drop_policy.reroll_shards_per_boss': 50.0,
    })
    assert out['income_source'] == 'qe_drop_policy_surfaces'
    assert out['total_weekly_reroll_income'] > 0

def test_shard_income_from_drop_qe():
    out = build_module_shard_income_calculator_from_drop_qe({
        'derived::runtime.eligible_bosses_per_run': 100,
        'derived::runtime.hours_per_run': 2.5,
        'derived::module.runtime_profile.farming_hours_per_day': 23.5,
        'planner.manual_policy.module.missions_per_week': 14,
        'derived::module.mission_policy.daily_mission_shards_bonus': 7,
        'derived::module.drop_policy.expected_shatter_equivalent_shards_per_boss': 0.165,
        'derived::module.resource_policy.gems_allocated_to_modules_per_week': 700,
    })
    assert out['income_exactness'] == 'partial_deterministic_shatter_equivalent'
    assert 'base_daily_mission_shards_unresolved' in out['blocked_reasons']
