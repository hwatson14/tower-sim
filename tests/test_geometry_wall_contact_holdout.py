from engine.geometry_wall_contact_fit_ingestion import build_wall_contact_fit_ingestion_scaffold
from engine.geometry_wall_contact_fit_harness import build_wall_contact_first_fit_harness
from engine.geometry_wall_contact_holdout import execute_holdout, build_candidate_acceptance_workflow


def test_holdout_executes_and_acceptance_builds():
    src = "templates/wall_contact_measurements_fit_ready_example.json"
    ingestion = build_wall_contact_fit_ingestion_scaffold(src)
    harness = build_wall_contact_first_fit_harness(src)
    holdout = execute_holdout(ingestion["valid_rows"], harness)
    assert holdout["status"] == "holdout_executed__promotion_blocked"
    assert holdout["candidate_results"]
    acceptance = build_candidate_acceptance_workflow(holdout)
    assert acceptance["status"] == "candidate_acceptance_built__promotion_blocked"
    assert acceptance["candidate_acceptance"]
