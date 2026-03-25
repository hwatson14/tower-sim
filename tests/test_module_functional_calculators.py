from compilers.module_reroll_income_calculator import build_module_reroll_income_calculator
from compilers.module_shard_income_calculator import build_module_shard_income_calculator
from compilers.module_slot_level_optimizer import build_module_slot_level_optimizer
from compilers.module_substat_optimizer import build_module_substat_optimizer
from compilers.module_reroll_spend_calculator import build_module_reroll_spend_calculator
from compilers.module_horizon_optimizer_outputs import build_module_horizon_optimizer_outputs
from compilers.module_planner_resource_state import build_module_planner_resource_state


def test_reroll_income_calculator():
    out = build_module_reroll_income_calculator(
        runtime_profile={"elites_per_run": 50, "hours_per_run": 2.5},
        farming_hours_per_day=23.5,
        cash_mastery_drop_chance_pct=4.0,
    )
    assert out["total_weekly_reroll_income"] > 0
    assert out["income_exactness"] == "advisory_assumed_drop_quantity"


def test_shard_income_calculator():
    out = build_module_shard_income_calculator(
        gems_allocated_to_modules_per_week=700,
        expected_shards_per_draw=2.5,
        manual_weekly_mission_shards=20,
    )
    assert out["draws_per_week"] == 35
    assert out["total_weekly_module_shards"] > 0


def test_slot_level_optimizer():
    top = {"top_candidates": [
        {"candidate_id": "cannon:primary:Alpha", "slot_id": "cannon", "upgrade_target": "primary", "rank": 1, "total_weighted_delta_raw": 10},
        {"candidate_id": "cannon:assist:Beta", "slot_id": "cannon", "upgrade_target": "assist", "rank": 2, "total_weighted_delta_raw": 8},
    ]}
    out = build_module_slot_level_optimizer(top, "cannon")
    assert out["best_primary_candidate"]["candidate_id"] == "cannon:primary:Alpha"
    assert out["best_assist_candidate"]["candidate_id"] == "cannon:assist:Beta"


def test_substat_optimizer():
    top = {"top_candidates": [
        {"candidate_id": "cannon:primary:Alpha", "action_family": "substat", "slot_id": "cannon", "substat_name": "cooldown", "rank": 1, "total_weighted_delta_raw": 10},
        {"candidate_id": "armor:assist:Beta", "action_family": "substat", "slot_id": "armor", "substat_name": "regen", "rank": 2, "total_weighted_delta_raw": 8},
    ]}
    out = build_module_substat_optimizer(top, objective_id="ehp", slot_id="cannon")
    assert out["candidate_count"] == 1


def test_reroll_spend_blocked_and_exact():
    blocked = build_module_reroll_spend_calculator(attempts=10)
    assert blocked["cost_exactness"] == "blocked_numeric_ladder_unclosed"
    exact = build_module_reroll_spend_calculator(attempts=10, base_cost_per_attempt=5, numeric_ladder_closed=True)
    assert exact["estimated_total_reroll_cost"] == 50


def test_horizon_optimizer_outputs():
    recommendation = {"candidate_id": "cannon:primary:Alpha", "request_id": "req_a"}
    top = {"top_candidates": [
        {"candidate_id": "cannon:primary:Alpha", "request_id": "req_a", "rank": 1, "total_weighted_delta_raw": 10},
        {"candidate_id": "cannon:assist:Beta", "request_id": "req_b", "rank": 2, "total_weighted_delta_raw": 8},
    ]}
    resources = build_module_planner_resource_state(10, 20, 100, 14, 23.5)
    out = build_module_horizon_optimizer_outputs(recommendation, top, resources, custom_days=10)
    assert set(out["available_horizons"]) == {"immediate", "week", "month", "custom"}
