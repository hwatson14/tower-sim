from __future__ import annotations

from typing import Any

def _substat_score(row: dict[str, Any], objective_id: str, cost_weight: float) -> float:
    benefit = float(row.get("objective_deltas", {}).get(objective_id, row.get("total_weighted_delta_raw", 0.0)))
    cost = float(row.get("reroll_cost", row.get("resource_cost", 0.0)) or 0.0)
    if cost_weight <= 0 or cost <= 0:
        return benefit
    return benefit - cost_weight * cost

def build_module_substat_optimizer(
    ranked_candidates: dict,
    objective_id: str,
    slot_id: str | None = None,
    cost_weight: float = 0.0,
) -> dict:
    if "top_candidates" not in ranked_candidates:
        raise ValueError("ranked_candidates.top_candidates required")
    rows = ranked_candidates["top_candidates"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("ranked_candidates.top_candidates must be a non-empty list")
    filtered = rows
    if slot_id is not None:
        filtered = [r for r in filtered if r.get("slot_id") == slot_id]
    substat_rows = [r for r in filtered if r.get("action_family") == "substat"]
    if not substat_rows:
        raise ValueError("no substat candidates found for requested filter")

    enriched = []
    for row in substat_rows:
        out = dict(row)
        benefit = float(row.get("objective_deltas", {}).get(objective_id, row.get("total_weighted_delta_raw", 0.0)))
        cost = float(row.get("reroll_cost", row.get("resource_cost", 0.0)) or 0.0)
        out["objective_id"] = objective_id
        out["objective_benefit"] = benefit
        out["optimizer_score"] = _substat_score(row, objective_id, cost_weight)
        out["benefit_to_cost"] = None if cost <= 0 else benefit / cost
        enriched.append(out)

    enriched.sort(key=lambda r: (-r["optimizer_score"], r.get("rank", 10**9)))
    best = enriched[0]

    grouped: dict[str, dict[str, Any]] = {}
    for row in enriched:
        key = str(row.get("substat_name", "unknown"))
        grouped.setdefault(key, {"substat_name": key, "best_candidate": row, "count": 0})
        grouped[key]["count"] += 1

    grouped_ranked = sorted(grouped.values(), key=lambda g: (-g["best_candidate"]["optimizer_score"], g["best_candidate"].get("rank", 10**9)))

    return {
        "objective_id": objective_id,
        "slot_id": slot_id,
        "cost_weight": float(cost_weight),
        "candidate_count": len(enriched),
        "best_substat_action": best,
        "ranked_substat_actions": enriched,
        "ranked_substat_groups": grouped_ranked,
        "substat_optimizer_exactness": "structural_with_cost_weight",
    }
