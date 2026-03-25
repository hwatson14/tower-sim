from engine.query_module_mission_economy import publish_module_mission_economy_surfaces
from compilers.module_shard_income_calculator import build_module_shard_income_calculator_from_drop_qe

class _Row:
    def __init__(self, final_value):
        self.final_value = final_value

def test_publish_module_mission_economy_surfaces():
    rows = {
        'derived::module.runtime_profile.highest_tier_unlocked': _Row(12.0),
        'derived::module.mission_policy.daily_mission_shards_bonus': _Row(7.0),
    }
    publish_module_mission_economy_surfaces(rows)
    assert rows['derived::module.mission_policy.base_daily_mission_shards'].final_value == 42.0
    assert rows['derived::module.mission_policy.total_daily_mission_shards'].final_value == 49.0

def test_shard_income_from_qe_uses_total_mission_shards():
    out = build_module_shard_income_calculator_from_drop_qe({
        'derived::runtime.eligible_bosses_per_run': 100,
        'derived::runtime.hours_per_run': 2.5,
        'derived::module.runtime_profile.farming_hours_per_day': 23.5,
        'planner.manual_policy.module.missions_per_week': 14,
        'derived::module.mission_policy.total_daily_mission_shards': 49,
        'derived::module.drop_policy.expected_shatter_equivalent_shards_per_boss': 0.165,
        'derived::module.resource_policy.gems_allocated_to_modules_per_week': 700,
    })
    assert out['daily_mission_total_shards_per_week'] == 686.0
    assert out['blocked_reasons'] == ['draw_policy_surfaces_unavailable']
