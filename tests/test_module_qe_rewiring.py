from compilers.module_planner_resource_state import build_module_planner_resource_state_from_qe
from compilers.module_reroll_income_calculator import build_module_reroll_income_calculator_from_qe
from compilers.module_shard_income_calculator import build_module_shard_income_calculator_from_qe
from compilers.module_horizon_optimizer_outputs import build_module_horizon_optimizer_outputs_from_qe
from engine.query_module_runtime_policy import publish_module_runtime_policy_surfaces


def test_planner_resource_state_from_qe_uses_published_surfaces():
    out = build_module_planner_resource_state_from_qe({
        "derived::economy.stock.reroll_shards": 10,
        "derived::economy.stock.module_shards": 20,
        "derived::module.resource_policy.gems_allocated_to_modules_per_week": 100,
        "derived::module.runtime_profile.farming_hours_per_day": 23.5,
    })
    assert out["reroll_shards_on_hand"] == 10
    assert out["module_shards_on_hand"] == 20
    assert out["gems_allocated_to_modules_per_week"] == 100
    assert out["farming_hours_per_day"] == 23.5
    assert out["resource_state_source"] == "qe_published_surfaces"
    assert out["missions_per_week"] is None
    assert "planner.manual_policy.module.missions_per_week" in out["missing_qe_surfaces"]


def test_planner_resource_state_from_qe_uses_missions_surface_when_present():
    out = build_module_planner_resource_state_from_qe({
        "derived::economy.stock.reroll_shards": 10,
        "derived::economy.stock.module_shards": 20,
        "derived::module.resource_policy.gems_allocated_to_modules_per_week": 100,
        "derived::module.runtime_profile.farming_hours_per_day": 23.5,
        "planner.manual_policy.module.missions_per_week": 14,
    })
    assert out["missions_per_week"] == 14
    assert out["resource_state_exactness"] == "qe_routed_manual_policy"
    assert out["missing_qe_surfaces"] == []


def test_module_runtime_policy_publishes_missions_surface(tmp_path):
    path = tmp_path / 'manual_advisory_inputs.json'
    path.write_text('{"inputs": [], "module": {"missions": {"per_week": 14}}}')
    rows = {}
    publish_module_runtime_policy_surfaces(rows, manual_input_path=path)
    assert "planner.manual_policy.module.missions_per_week" in rows
    assert rows["planner.manual_policy.module.missions_per_week"].final_value == 14


def test_reroll_income_calculator_from_qe_uses_externalized_surface():
    out = build_module_reroll_income_calculator_from_qe({
        "derived::economy.income.reroll_shards": 654,
        "derived::module.runtime_profile.farming_hours_per_day": 23.5,
    })
    assert out["total_weekly_reroll_income"] == 654
    assert out["income_source"] == "qe_published_surface"


def test_shard_income_calculator_from_qe_uses_externalized_surface():
    out = build_module_shard_income_calculator_from_qe({
        "derived::economy.income.module_shards": 321,
        "derived::module.resource_policy.gems_allocated_to_modules_per_week": 700,
    })
    assert out["total_weekly_module_shards"] == 321
    assert out["gems_allocated_to_modules_per_week"] == 700
    assert out["income_source"] == "qe_published_surface"


def test_horizon_optimizer_outputs_from_qe_builds_from_qe_state():
    recommendation = {"candidate_id": "cannon:primary:Alpha", "request_id": "req_a"}
    top = {"top_candidates": [
        {"candidate_id": "cannon:primary:Alpha", "request_id": "req_a", "rank": 1, "total_weighted_delta_raw": 10},
        {"candidate_id": "cannon:assist:Beta", "request_id": "req_b", "rank": 2, "total_weighted_delta_raw": 8},
    ]}
    out = build_module_horizon_optimizer_outputs_from_qe(
        recommendation,
        top,
        {
            "derived::economy.stock.reroll_shards": 10,
            "derived::economy.stock.module_shards": 20,
            "derived::module.resource_policy.gems_allocated_to_modules_per_week": 100,
            "derived::module.runtime_profile.farming_hours_per_day": 23.5,
            "planner.manual_policy.module.missions_per_week": 14,
        },
        custom_days=10,
    )
    assert set(out["available_horizons"]) == {"immediate", "week", "month", "custom"}
    assert out["resource_state_source"] == "qe_published_surfaces"
    assert out["missing_qe_surfaces"] == []
