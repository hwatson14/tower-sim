from __future__ import annotations

def build_module_planner_plan(
    horizon_profile: dict,
    resource_state: dict,
    action_candidates: dict,
    recommendation: dict,
) -> dict:
    for obj, key in [
        (horizon_profile, "horizon_kind"),
        (resource_state, "resource_state_exactness"),
        (action_candidates, "immediate_action"),
        (recommendation, "candidate_id"),
    ]:
        if key not in obj:
            raise ValueError(f"missing required key: {key}")

    recommended_action = action_candidates["immediate_action"]
    if recommended_action["candidate_id"] != recommendation["candidate_id"]:
        raise ValueError("immediate action must match recommendation candidate")

    horizon_kind = horizon_profile["horizon_kind"]
    if horizon_kind == "immediate":
        plan_mode = "next_best_change"
    else:
        plan_mode = "advisory_horizon_plan"

    exactness = "advisory_until_costs_closed"
    if action_candidates.get("cost_exactness") == "exact":
        exactness = "exact_with_costs"

    return {
        "horizon_profile": horizon_profile,
        "resource_state": resource_state,
        "plan_mode": plan_mode,
        "recommended_action": recommended_action,
        "candidate_actions": action_candidates["candidate_actions"],
        "recommendation_evidence": {
            "candidate_id": recommendation["candidate_id"],
            "request_id": recommendation.get("request_id"),
        },
        "planner_exactness": exactness,
    }
