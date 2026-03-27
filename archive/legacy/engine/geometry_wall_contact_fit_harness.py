from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt
from typing import Any, Dict, List, Sequence

from engine.geometry_wall_contact_fit_ingestion import build_wall_contact_fit_ingestion_scaffold
from engine.geometry_wall_contact_target_surface import CANONICAL_TARGET_SURFACE

FIT_HARNESS_VERSION = "wall_contact_fit_harness_v2"


@dataclass(frozen=True)
class FitCandidate:
    family_id: str
    target_surface: str
    predictor_surface: str | None
    parameters: Dict[str, Any]
    row_count: int
    rmse: float
    mae: float
    max_abs_error: float
    monotonic_non_decreasing: bool
    holdout_ready: bool
    promotion_blocked: bool = True
    promotion_block_reason: str = "Candidate-only fit harness. Promotion remains blocked."


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _metrics(actuals: Sequence[float], preds: Sequence[float]) -> Dict[str, float]:
    errs = [p - a for a, p in zip(actuals, preds)]
    abs_errs = [abs(e) for e in errs]
    mse = _mean([e * e for e in errs]) if errs else 0.0
    return {"rmse": sqrt(mse), "mae": _mean(abs_errs), "max_abs_error": max(abs_errs) if abs_errs else 0.0}


def _fit_affine(xs: Sequence[float], ys: Sequence[float]) -> Dict[str, float]:
    n = len(xs)
    if n < 2:
        raise ValueError("Need at least 2 rows for affine fit.")
    x_bar = _mean(xs)
    y_bar = _mean(ys)
    sxx = sum((x - x_bar) ** 2 for x in xs)
    if sxx == 0:
        return {"slope": 0.0, "intercept": y_bar}
    sxy = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = y_bar - slope * x_bar
    return {"slope": slope, "intercept": intercept}


def _predict_affine(x: float, params: Dict[str, float]) -> float:
    return params["slope"] * x + params["intercept"]


def _monotonic_non_decreasing(xs: Sequence[float], preds: Sequence[float]) -> bool:
    pairs = sorted(zip(xs, preds), key=lambda t: t[0])
    return all(b >= a for (_, a), (_, b) in zip(pairs, pairs[1:]))


def _fit_candidate(rows: Sequence[Dict[str, Any]], family_id: str, predictor_surface: str) -> FitCandidate:
    xs = [float(r[predictor_surface]) for r in rows]
    ys = [float(r[CANONICAL_TARGET_SURFACE]) for r in rows]
    params = _fit_affine(xs, ys)
    preds = [_predict_affine(x, params) for x in xs]
    return FitCandidate(
        family_id=family_id,
        target_surface=CANONICAL_TARGET_SURFACE,
        predictor_surface=predictor_surface,
        parameters=params,
        row_count=len(rows),
        monotonic_non_decreasing=_monotonic_non_decreasing(xs, preds),
        holdout_ready=len(rows) >= 8,
        **_metrics(ys, preds),
    )


def _fit_displayed_equality_baseline(rows: Sequence[Dict[str, Any]]) -> FitCandidate:
    xs = [float(r["wall_radius_displayed_m"]) for r in rows]
    ys = [float(r[CANONICAL_TARGET_SURFACE]) for r in rows]
    preds = xs[:]
    return FitCandidate(
        family_id="displayed_equality_baseline",
        target_surface=CANONICAL_TARGET_SURFACE,
        predictor_surface="wall_radius_displayed_m",
        parameters={"identity": 1.0},
        row_count=len(rows),
        monotonic_non_decreasing=_monotonic_non_decreasing(xs, preds),
        holdout_ready=len(rows) >= 8,
        **_metrics(ys, preds),
    )


def _fit_piecewise_displayed(rows: Sequence[Dict[str, Any]]) -> FitCandidate:
    low = [r for r in rows if float(r["tower_range_theoretical_m"]) <= 80.0]
    high = [r for r in rows if float(r["tower_range_theoretical_m"]) > 80.0]
    if len(low) < 2 or len(high) < 2:
        return _fit_candidate(rows, "piecewise_displayed_fallback_affine", "wall_radius_displayed_m")
    low_params = _fit_affine([float(r["wall_radius_displayed_m"]) for r in low], [float(r[CANONICAL_TARGET_SURFACE]) for r in low])
    high_params = _fit_affine([float(r["wall_radius_displayed_m"]) for r in high], [float(r[CANONICAL_TARGET_SURFACE]) for r in high])
    xs = [float(r["wall_radius_displayed_m"]) for r in rows]
    ys = [float(r[CANONICAL_TARGET_SURFACE]) for r in rows]
    preds = [
        _predict_affine(x, low_params if float(r["tower_range_theoretical_m"]) <= 80.0 else high_params)
        for r, x in zip(rows, xs)
    ]
    return FitCandidate(
        family_id="piecewise_displayed_fit",
        target_surface=CANONICAL_TARGET_SURFACE,
        predictor_surface="wall_radius_displayed_m",
        parameters={"le_80": low_params, "gt_80": high_params, "split_theoretical_m": 80.0},
        row_count=len(rows),
        monotonic_non_decreasing=_monotonic_non_decreasing(xs, preds),
        holdout_ready=len(rows) >= 8,
        **_metrics(ys, preds),
    )


def build_wall_contact_first_fit_harness(path: str) -> Dict[str, Any]:
    ingestion = build_wall_contact_fit_ingestion_scaffold(path)
    readiness = ingestion["readiness"]["status"]
    if readiness != "fit_ready":
        return {
            "status": "fit_harness_blocked__dataset_not_fit_ready",
            "version": FIT_HARNESS_VERSION,
            "canonical_target_surface": CANONICAL_TARGET_SURFACE,
            "readiness": ingestion["readiness"],
            "row_count": len(ingestion["valid_rows"]),
            "candidates": [],
        }
    rows = ingestion["valid_rows"]
    candidates = [
        _fit_displayed_equality_baseline(rows),
        _fit_candidate(rows, "displayed_affine_fit", "wall_radius_displayed_m"),
        _fit_candidate(rows, "tower_displayed_affine_fit", "tower_range_displayed_m"),
        _fit_piecewise_displayed(rows),
    ]
    best = min(candidates, key=lambda c: c.rmse)
    return {
        "status": "candidate_fits_built__promotion_blocked",
        "version": FIT_HARNESS_VERSION,
        "canonical_target_surface": CANONICAL_TARGET_SURFACE,
        "readiness": ingestion["readiness"],
        "row_count": len(rows),
        "best_candidate_family_id": best.family_id,
        "candidates": [asdict(c) for c in candidates],
    }
