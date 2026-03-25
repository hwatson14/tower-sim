from __future__ import annotations

from compilers.module_planner_horizon_profile import build_module_planner_horizon_profile
from compilers.module_planner_plan import build_module_planner_plan
from compilers.module_planner_action_candidates import build_module_planner_action_candidates
from compilers.module_planner_resource_state import build_module_planner_resource_state_from_qe


def build_module_horizon_optimizer_outputs(
    recommendation: dict,
    top_candidates: dict,
    resource_state: dict,
    custom_days: int | None = None,
) -> dict:
    horizons = ["immediate", "week", "month", "custom"]
    outputs = {}
    actions = build_module_planner_action_candidates(recommendation, top_candidates)
    for horizon_kind in horizons:
        if horizon_kind == "custom":
            if custom_days is None:
                continue
            horizon = build_module_planner_horizon_profile("custom", custom_days)
        else:
            horizon = build_module_planner_horizon_profile(horizon_kind)
        outputs[horizon_kind] = build_module_planner_plan(horizon, resource_state, actions, recommendation)
    return {
        "horizon_outputs": outputs,
        "available_horizons": list(outputs.keys()),
    }


def build_module_horizon_optimizer_outputs_from_qe(
    recommendation: dict,
    top_candidates: dict,
    qe_surfaces: dict,
    custom_days: int | None = None,
) -> dict:
    resource_state = build_module_planner_resource_state_from_qe(qe_surfaces)
    result = build_module_horizon_optimizer_outputs(
        recommendation, top_candidates, resource_state, custom_days=custom_days,
    )
    result["resource_state_source"] = resource_state.get("resource_state_source", "qe_published_surfaces")
    result["missing_qe_surfaces"] = resource_state.get("missing_qe_surfaces", [])
    return result
