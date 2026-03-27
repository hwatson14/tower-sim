from __future__ import annotations

from typing import Any, Dict

from .geometry_wall_contact_artifact_harmonizer import harmonize_wall_contact_fit_path_artifacts
from .geometry_wall_contact_fit_harness import build_wall_contact_first_fit_harness
from .geometry_wall_contact_fit_ingestion import build_wall_contact_fit_ingestion_scaffold
from .geometry_wall_contact_fit_review import build_wall_contact_fit_review_report
from .geometry_wall_contact_holdout import build_candidate_acceptance_workflow, execute_holdout
from .geometry_wall_contact_fit_decision import build_wall_contact_fit_decision_report
from .geometry_wall_contact_target_surface import CANONICAL_TARGET_SURFACE


def build_wall_contact_fit_pipeline(path: str) -> Dict[str, Any]:
    ingestion = build_wall_contact_fit_ingestion_scaffold(path)
    harness = build_wall_contact_first_fit_harness(path)
    review = build_wall_contact_fit_review_report(harness)
    rows = ingestion.get("valid_rows", [])
    holdout = execute_holdout(rows, harness)
    acceptance = build_candidate_acceptance_workflow(holdout)
    decision = build_wall_contact_fit_decision_report(review, holdout, acceptance)
    harmonized = harmonize_wall_contact_fit_path_artifacts(
        {
            "ingestion": ingestion,
            "fit_harness": harness,
            "fit_review": review,
            "holdout": holdout,
            "acceptance_workflow": acceptance,
            "fit_decision": decision,
        }
    )
    return {
        "status": "fit_pipeline_rebased_subset_completed__promotion_blocked",
        "promotion_status": "blocked",
        "canonical_target_surface": CANONICAL_TARGET_SURFACE,
        "ingestion": ingestion,
        "fit_harness": harness,
        "fit_review": review,
        "holdout": holdout,
        "acceptance_workflow": acceptance,
        "fit_decision": decision,
        "harmonization": harmonized,
        "notes": [
            "This selective rebase pack ports ingestion, fit harness, review, holdout, and decision layers into r80.",
            "Promotion remains blocked and broader runtime geometry integration is still out of scope for this selective rebase.",
        ],
    }
