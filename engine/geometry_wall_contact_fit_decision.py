from __future__ import annotations

from typing import Any, Dict, List

DECISION_VERSION = "wall_contact_fit_decision_v1"


def build_wall_contact_fit_decision_report(
    review_report: Dict[str, Any],
    holdout_report: Dict[str, Any],
    acceptance_workflow: Dict[str, Any],
) -> Dict[str, Any]:
    if review_report.get("status") != "fit_review_built__promotion_blocked" or holdout_report.get("status") != "holdout_executed__promotion_blocked":
        return {
            "status": "fit_decision_blocked__upstream_not_ready",
            "version": DECISION_VERSION,
            "promotion_status": "blocked",
            "candidate_decisions": [],
        }

    review_by_family = {e["family_id"]: e for e in review_report.get("review_entries", [])}
    holdout_by_family = {e["family_id"]: e for e in holdout_report.get("candidate_results", [])}
    acceptance_by_family = {e["family_id"]: e for e in acceptance_workflow.get("candidate_acceptance", [])}

    families = sorted(set(review_by_family) | set(holdout_by_family) | set(acceptance_by_family))
    decisions: List[Dict[str, Any]] = []
    for family in families:
        review = review_by_family.get(family, {})
        holdout = holdout_by_family.get(family, {})
        acceptance = acceptance_by_family.get(family, {})
        blocking_reasons: List[str] = []
        blocking_reasons.extend(review.get("reasons", []))
        blocking_reasons.extend(acceptance.get("reasons", []))
        decision_status = acceptance.get("status") or review.get("review_outcome") or "blocked"
        decisions.append({
            "family_id": family,
            "decision_status": decision_status,
            "review_outcome": review.get("review_outcome"),
            "holdout_global_metrics": holdout.get("global_metrics"),
            "accepted_for_promotion": False,
            "blocking_reasons": blocking_reasons,
        })

    recommended = None
    acceptable = [d for d in decisions if d["decision_status"] == "candidate_conditionally_acceptable__promotion_still_blocked"]
    if acceptable:
        recommended = min(acceptable, key=lambda d: (d.get("holdout_global_metrics") or {}).get("rmse", float("inf")))

    return {
        "status": "fit_decision_built__promotion_blocked",
        "version": DECISION_VERSION,
        "promotion_status": "blocked",
        "best_candidate_family_id": review_report.get("best_candidate_family_id"),
        "recommended_candidate_family_id": recommended["family_id"] if recommended else None,
        "candidate_decisions": decisions,
        "notes": [
            "Integrated decision layer merges review, holdout, and candidate acceptance outcomes.",
            "Promotion remains blocked pending human review and broader version/regime checks.",
        ],
    }
