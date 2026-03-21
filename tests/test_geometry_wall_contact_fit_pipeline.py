from engine.geometry_wall_contact_fit_pipeline import build_wall_contact_fit_pipeline


def test_fit_pipeline_builds_full_selective_rebase_path():
    report = build_wall_contact_fit_pipeline("templates/wall_contact_measurements_fit_ready_example.json")
    assert report["status"] == "fit_pipeline_rebased_subset_completed__promotion_blocked"
    assert report["fit_review"]["status"] == "fit_review_built__promotion_blocked"
    assert report["holdout"]["status"] == "holdout_executed__promotion_blocked"
    assert report["acceptance_workflow"]["status"] == "candidate_acceptance_built__promotion_blocked"
    assert report["fit_decision"]["status"] == "fit_decision_built__promotion_blocked"
