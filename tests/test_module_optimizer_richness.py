from compilers.module_slot_level_optimizer import build_module_slot_level_optimizer
from compilers.module_substat_optimizer import build_module_substat_optimizer

def test_slot_level_optimizer_prefers_assist_when_primary_is_too_expensive():
    ranked = {
        "top_candidates": [
            {"candidate_id": "p1", "slot_id": "cannon", "upgrade_target": "primary", "total_weighted_delta_raw": 100.0, "resource_cost": 100.0, "rank": 1},
            {"candidate_id": "a1", "slot_id": "cannon", "upgrade_target": "assist", "total_weighted_delta_raw": 80.0, "resource_cost": 10.0, "rank": 2},
            {"candidate_id": "p2", "slot_id": "armor", "upgrade_target": "primary", "total_weighted_delta_raw": 200.0, "resource_cost": 10.0, "rank": 1},
        ]
    }
    out = build_module_slot_level_optimizer(ranked, slot_id="cannon", cost_weight=1.0)
    assert out["best_primary_candidate"]["candidate_id"] == "p1"
    assert out["best_assist_candidate"]["candidate_id"] == "a1"
    assert out["recommended_slot_action"]["candidate_id"] == "a1"

def test_slot_level_optimizer_prefers_primary_when_cost_weight_zero():
    ranked = {
        "top_candidates": [
            {"candidate_id": "p1", "slot_id": "generator", "upgrade_target": "primary", "total_weighted_delta_raw": 100.0, "resource_cost": 100.0, "rank": 1},
            {"candidate_id": "a1", "slot_id": "generator", "upgrade_target": "assist", "total_weighted_delta_raw": 80.0, "resource_cost": 10.0, "rank": 2},
        ]
    }
    out = build_module_slot_level_optimizer(ranked, slot_id="generator", cost_weight=0.0)
    assert out["recommended_slot_action"]["candidate_id"] == "p1"

def test_substat_optimizer_uses_objective_specific_delta_and_cost():
    ranked = {
        "top_candidates": [
            {
                "candidate_id": "s1",
                "action_family": "substat",
                "slot_id": "core",
                "substat_name": "cooldown",
                "objective_deltas": {"eecon": 12.0, "edamage": 2.0},
                "reroll_cost": 5.0,
                "rank": 1,
            },
            {
                "candidate_id": "s2",
                "action_family": "substat",
                "slot_id": "core",
                "substat_name": "multiplier",
                "objective_deltas": {"eecon": 10.0, "edamage": 15.0},
                "reroll_cost": 1.0,
                "rank": 2,
            },
        ]
    }
    out = build_module_substat_optimizer(ranked, objective_id="eecon", slot_id="core", cost_weight=1.0)
    assert out["best_substat_action"]["candidate_id"] == "s2"
    assert out["ranked_substat_groups"][0]["substat_name"] == "multiplier"

def test_substat_optimizer_can_change_winner_by_cost_weight():
    ranked = {
        "top_candidates": [
            {
                "candidate_id": "s1",
                "action_family": "substat",
                "slot_id": "armor",
                "substat_name": "regen",
                "objective_deltas": {"ehp": 20.0},
                "reroll_cost": 30.0,
                "rank": 1,
            },
            {
                "candidate_id": "s2",
                "action_family": "substat",
                "slot_id": "armor",
                "substat_name": "def_pct",
                "objective_deltas": {"ehp": 12.0},
                "reroll_cost": 1.0,
                "rank": 2,
            },
        ]
    }
    out = build_module_substat_optimizer(ranked, objective_id="ehp", slot_id="armor", cost_weight=1.0)
    assert out["best_substat_action"]["candidate_id"] == "s2"
