from pytest import approx
from engine.query_module_lab_policy import publish_module_lab_policy_surfaces
from engine.query_module_drop_economy import publish_module_drop_economy_surfaces

class _Row:
    def __init__(self, final_value):
        self.final_value = final_value

def test_publish_module_lab_policy_surfaces():
    rows = {}
    publish_module_lab_policy_surfaces(rows, {
        'Reroll Shards': 12,
        'Common Drop Chance': 3,
        'Rare Drop Chance': 4,
        'Daily Mission Shards': 7,
        'Shatter Shards': 2,
    })
    assert rows['derived::module.lab.reroll_shards_bonus'].final_value == 12.0
    assert rows['derived::module.lab.common_drop_chance_bonus_pct'].final_value == approx(0.3)
    assert rows['derived::module.lab.rare_drop_chance_bonus_pct'].final_value == approx(0.4)
    assert rows['derived::module.lab.daily_mission_shards_bonus'].final_value == 7.0
    assert rows['derived::module.lab.shatter_shards_bonus_pct'].final_value == 40.0

def test_publish_module_drop_economy_surfaces_uses_qe_surfaces_not_manual_inputs():
    rows = {
        'derived::module.runtime_profile.farming_tier': _Row(12.0),
        'derived::module.lab.reroll_shards_bonus': _Row(12.0),
        'derived::module.lab.common_drop_chance_bonus_pct': _Row(0.3),
        'derived::module.lab.rare_drop_chance_bonus_pct': _Row(0.2),
        'derived::module.lab.daily_mission_shards_bonus': _Row(7.0),
        'derived::module.lab.shatter_shards_bonus_pct': _Row(40.0),
    }
    publish_module_drop_economy_surfaces(rows)
    assert rows['derived::module.drop_policy.reroll_shards_per_boss'].final_value == 57.0
    assert rows['derived::module.drop_policy.common_module_drop_chance_pct'].final_value == 2.3
    assert rows['derived::module.shatter_policy.common_module_shards'].final_value == 7.0
    assert rows['derived::module.mission_policy.daily_mission_shards_bonus'].final_value == 7.0
