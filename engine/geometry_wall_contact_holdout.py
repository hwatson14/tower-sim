from __future__ import annotations

from math import sqrt
from typing import Any, Dict, Iterable, List, Tuple

from engine.geometry_wall_contact_fit_harness import _fit_affine, _predict_affine
from engine.geometry_wall_contact_target_surface import CANONICAL_TARGET_SURFACE

HOLDOUT_VERSION = "wall_contact_holdout_v1"


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _metrics(actuals: List[float], preds: List[float]) -> Dict[str, float]:
    errs = [p - a for a, p in zip(actuals, preds)]
    abs_errs = [abs(e) for e in errs]
    mse = _mean([e * e for e in errs]) if errs else 0.0
    return {"rmse": sqrt(mse), "mae": _mean(abs_errs), "max_abs_error": max(abs_errs) if abs_errs else 0.0}


def _split_train_holdout(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    ordered = sorted(rows, key=lambda r: float(r["tower_range_theoretical_m"]))
    holdout = ordered[::3]
    holdout_ids = {id(r) for r in holdout}
    train = [r for r in ordered if id(r) not in holdout_ids]
    if len(train) < 4 or len(holdout) < 2:
        # fall back to a 75/25 split
        n = len(ordered)
        cut = max(1, int(round(n * 0.75)))
        train, holdout = ordered[:cut], ordered[cut:]
    return train, holdout


def _predict_candidate(candidate: Dict[str, Any], row: Dict[str, Any]) -> float:
    family = candidate["family_id"]
    if family == "displayed_equality_baseline":
        return float(row["wall_radius_displayed_m"])
    if family == "displayed_affine_fit":
        return _predict_affine(float(row["wall_radius_displayed_m"]), candidate["parameters"])
    if family == "tower_displayed_affine_fit":
        return _predict_affine(float(row["tower_range_displayed_m"]), candidate["parameters"])
    if family == "piecewise_displayed_fit":
        params = candidate["parameters"]["le_80" if float(row["tower_range_theoretical_m"]) <= 80.0 else "gt_80"]
        return _predict_affine(float(row["wall_radius_displayed_m"]), params)
    # fallback for future/unknown candidates
    predictor = candidate.get("predictor_surface") or "wall_radius_displayed_m"
    params = candidate.get("parameters", {})
    if isinstance(params, dict) and "slope" in params and "intercept" in params:
        return _predict_affine(float(row[predictor]), params)
    return float(row[CANONICAL_TARGET_SURFACE])


def _band_metrics(rows: List[Dict[str, Any]], preds: List[float]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for label, selector in {
        "le_80_theoretical": lambda r: float(r["tower_range_theoretical_m"]) <= 80.0,
        "gt_80_theoretical": lambda r: float(r["tower_range_theoretical_m"]) > 80.0,
    }.items():
        actuals = [float(r[CANONICAL_TARGET_SURFACE]) for r in rows if selector(r)]
        sub_preds = [p for r, p in zip(rows, preds) if selector(r)]
        out[label] = _metrics(actuals, sub_preds) if actuals else {"rmse": 0.0, "mae": 0.0, "max_abs_error": 0.0}
    return out


def execute_holdout(rows: List[Dict[str, Any]], harness_report: Dict[str, Any]) -> Dict[str, Any]:
    if harness_report.get("status") != "candidate_fits_built__promotion_blocked":
        return {
            "status": "holdout_blocked__harness_not_ready",
            "version": HOLDOUT_VERSION,
            "canonical_target_surface": harness_report.get("canonical_target_surface"),
            "candidate_results": [],
        }
    train_rows, holdout_rows = _split_train_holdout(rows)
    candidate_results: List[Dict[str, Any]] = []
    for candidate in harness_report.get("candidates", []):
        preds = [_predict_candidate(candidate, row) for row in holdout_rows]
        actuals = [float(r[CANONICAL_TARGET_SURFACE]) for r in holdout_rows]
        candidate_results.append({
            "family_id": candidate["family_id"],
            "global_metrics": _metrics(actuals, preds),
            "band_metrics": _band_metrics(holdout_rows, preds),
            "holdout_ready": True,
        })
    return {
        "status": "holdout_executed__promotion_blocked",
        "version": HOLDOUT_VERSION,
        "canonical_target_surface": harness_report.get("canonical_target_surface"),
        "train_row_count": len(train_rows),
        "holdout_row_count": len(holdout_rows),
        "candidate_results": candidate_results,
        "holdout_preview": {
            "train_theoretical_ranges": [float(r["tower_range_theoretical_m"]) for r in train_rows],
            "holdout_theoretical_ranges": [float(r["tower_range_theoretical_m"]) for r in holdout_rows],
        },
    }


def build_candidate_acceptance_workflow(holdout_report: Dict[str, Any]) -> Dict[str, Any]:
    if holdout_report.get("status") != "holdout_executed__promotion_blocked":
        return {
            "status": "candidate_acceptance_blocked__holdout_not_ready",
            "version": HOLDOUT_VERSION,
            "candidate_acceptance": [],
        }
    acceptance: List[Dict[str, Any]] = []
    for result in holdout_report.get("candidate_results", []):
        reasons: List[str] = []
        g = result["global_metrics"]
        if g["rmse"] > 5.0:
            reasons.append("global rmse exceeds threshold")
        if g["mae"] > 4.0:
            reasons.append("global mae exceeds threshold")
        for band_name, band_metrics in result["band_metrics"].items():
            if band_metrics["rmse"] > 6.0:
                reasons.append(f"{band_name} rmse exceeds threshold")
        status = "candidate_rejected__more_review_needed" if reasons else "candidate_conditionally_acceptable__promotion_still_blocked"
        acceptance.append({
            "family_id": result["family_id"],
            "status": status,
            "reasons": reasons,
            "accepted_for_promotion": False,
        })
    return {
        "status": "candidate_acceptance_built__promotion_blocked",
        "version": HOLDOUT_VERSION,
        "candidate_acceptance": acceptance,
    }
