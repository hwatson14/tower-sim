from __future__ import annotations

from typing import Any, Dict, List

FIT_REVIEW_VERSION = "wall_contact_fit_review_v1"


def _band_assessment(candidate: Dict[str, Any]) -> Dict[str, Any]:
    family = candidate.get("family_id", "unknown")
    # Current selective rebase does not yet have true band residuals; review records this explicitly.
    return {
        "status": "band_review_partial__no_true_band_residuals_yet",
        "family_id": family,
        "bands_reviewed": ["le_80_theoretical", "gt_80_theoretical"],
    }


def build_wall_contact_fit_review_report(harness_report: Dict[str, Any]) -> Dict[str, Any]:
    if harness_report.get("status") != "candidate_fits_built__promotion_blocked":
        return {
            "status": "fit_review_blocked__harness_not_ready",
            "version": FIT_REVIEW_VERSION,
            "canonical_target_surface": harness_report.get("canonical_target_surface"),
            "review_entries": [],
            "promotion_readiness": {"status": "blocked"},
        }

    entries: List[Dict[str, Any]] = []
    for candidate in harness_report.get("candidates", []):
        reasons: List[str] = []
        if not candidate.get("monotonic_non_decreasing", False):
            reasons.append("candidate is not monotonic non-decreasing")
        if not candidate.get("holdout_ready", False):
            reasons.append("candidate not holdout-ready")
        # First-pass governance thresholds only.
        if float(candidate.get("rmse", 0.0)) > 5.0:
            reasons.append("rmse exceeds first-pass review threshold")
        outcome = "candidate_needs_more_review" if reasons else "candidate_passes_first_pass_review__promotion_still_blocked"
        entries.append({
            "family_id": candidate.get("family_id"),
            "target_surface": candidate.get("target_surface"),
            "review_outcome": outcome,
            "reasons": reasons,
            "residual_band_assessment": _band_assessment(candidate),
            "holdout_assessment": "holdout_ready" if candidate.get("holdout_ready", False) else "holdout_not_ready",
            "promotion_ready": False,
            "accepted_for_promotion": False,
        })

    best_family = harness_report.get("best_candidate_family_id")
    return {
        "status": "fit_review_built__promotion_blocked",
        "version": FIT_REVIEW_VERSION,
        "canonical_target_surface": harness_report.get("canonical_target_surface"),
        "best_candidate_family_id": best_family,
        "review_entries": entries,
        "promotion_readiness": {
            "status": "blocked",
            "reason": "Review layer never auto-promotes candidates.",
        },
    }
