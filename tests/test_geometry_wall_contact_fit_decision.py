from engine.geometry_wall_contact_fit_harness import build_wall_contact_first_fit_harness
from engine.geometry_wall_contact_fit_ingestion import build_wall_contact_fit_ingestion_scaffold
from engine.geometry_wall_contact_fit_review import build_wall_contact_fit_review_report
from engine.geometry_wall_contact_holdout import execute_holdout, build_candidate_acceptance_workflow
from engine.geometry_wall_contact_fit_decision import build_wall_contact_fit_decision_report


def test_fit_decision_builds_from_review_holdout_acceptance():
    src = "templates/wall_contact_measurements_fit_ready_example.json"
    ingestion = build_wall_contact_fit_ingestion_scaffold(src)
    harness = build_wall_contact_first_fit_harness(src)
    review = build_wall_contact_fit_review_report(harness)
    holdout = execute_holdout(ingestion["valid_rows"], harness)
    acceptance = build_candidate_acceptance_workflow(holdout)
    decision = build_wall_contact_fit_decision_report(review, holdout, acceptance)
    assert decision["status"] == "fit_decision_built__promotion_blocked"
    assert decision["promotion_status"] == "blocked"
    assert decision["candidate_decisions"]
