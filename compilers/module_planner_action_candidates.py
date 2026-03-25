from __future__ import annotations

def build_module_planner_action_candidates(
    recommendation: dict,
    top_candidates: dict,
    cost_exactness: str = "blocked_partial",
) -> dict:
    if not recommendation or "candidate_id" not in recommendation:
        raise ValueError("recommendation with candidate_id required")
    if not top_candidates or "top_candidates" not in top_candidates:
        raise ValueError("top_candidates payload required")

    ranked = top_candidates["top_candidates"]
    if not isinstance(ranked, list) or not ranked:
        raise ValueError("top_candidates.top_candidates must be a non-empty list")

    actions = []
    seen = set()
    for row in ranked:
        cid = row.get("candidate_id")
        if not cid or cid in seen:
            raise ValueError("candidate_ids must be present and unique")
        seen.add(cid)
        actions.append({
            "candidate_id": cid,
            "request_id": row.get("request_id"),
            "rank": row.get("rank"),
            "total_weighted_delta_raw": row.get("total_weighted_delta_raw"),
            "action_kind": "loadout_change",
            "cost_exactness": cost_exactness,
            "cost_status": "not_yet_computed" if cost_exactness != "exact" else "available",
        })

    immediate = next((a for a in actions if a["candidate_id"] == recommendation["candidate_id"]), None)
    if immediate is None:
        raise ValueError("recommendation candidate must exist in top_candidates")

    return {
        "immediate_action": immediate,
        "candidate_actions": actions,
        "cost_exactness": cost_exactness,
    }
