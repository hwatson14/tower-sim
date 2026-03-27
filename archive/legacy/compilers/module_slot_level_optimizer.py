from __future__ import annotations

from typing import Any

def _score_candidate(row: dict[str, Any], cost_weight: float) -> float:
    benefit = float(row.get("total_weighted_delta_raw", 0.0))
    cost = float(row.get("resource_cost", 0.0) or 0.0)
    if cost_weight <= 0 or cost <= 0:
        return benefit
    return benefit - (cost_weight * cost)

def build_module_slot_level_optimizer(
    ranked_candidates: dict,
    slot_id: str,
    cost_weight: float = 0.0,
) -> dict:
    if "top_candidates" not in ranked_candidates:
        raise ValueError("ranked_candidates.top_candidates required")
    rows = ranked_candidates["top_candidates"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("ranked_candidates.top_candidates must be a non-empty list")

    slot_rows = [r for r in rows if r.get("slot_id") == slot_id]
    if not slot_rows:
        raise ValueError(f"no ranked candidates found for slot_id={slot_id}")

    primary_rows = [r for r in slot_rows if r.get("upgrade_target") == "primary"]
    assist_rows = [r for r in slot_rows if r.get("upgrade_target") == "assist"]

    if not primary_rows and not assist_rows:
        raise ValueError(f"slot_id={slot_id} has no primary or assist upgrade candidates")

    def enrich(row: dict[str, Any]) -> dict[str, Any]:
        out = dict(row)
        out["optimizer_score"] = _score_candidate(row, cost_weight)
        benefit = float(row.get("total_weighted_delta_raw", 0.0))
        cost = float(row.get("resource_cost", 0.0) or 0.0)
        out["benefit_to_cost"] = None if cost <= 0 else benefit / cost
        return out

    primary_ranked = sorted((enrich(r) for r in primary_rows), key=lambda r: (-r["optimizer_score"], r.get("rank", 10**9)))
    assist_ranked = sorted((enrich(r) for r in assist_rows), key=lambda r: (-r["optimizer_score"], r.get("rank", 10**9)))

    best_primary = primary_ranked[0] if primary_ranked else None
    best_assist = assist_ranked[0] if assist_ranked else None

    options = [x for x in [best_primary, best_assist] if x is not None]
    recommended = sorted(options, key=lambda r: (-r["optimizer_score"], r.get("rank", 10**9)))[0]

    return {
        "slot_id": slot_id,
        "cost_weight": float(cost_weight),
        "best_primary_candidate": best_primary,
        "best_assist_candidate": best_assist,
        "recommended_slot_action": recommended,
        "slot_optimizer_exactness": "structural_with_cost_weight",
    }
