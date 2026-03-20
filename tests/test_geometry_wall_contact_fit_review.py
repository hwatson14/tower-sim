from engine.geometry_wall_contact_fit_harness import build_wall_contact_first_fit_harness
from engine.geometry_wall_contact_fit_review import build_wall_contact_fit_review_report


def test_fit_review_builds_from_harness(tmp_path):
    src = "templates/wall_contact_measurements_fit_ready_example.json"
    harness = build_wall_contact_first_fit_harness(src)
    report = build_wall_contact_fit_review_report(harness)
    assert report["status"] == "fit_review_built__promotion_blocked"
    assert report["promotion_readiness"]["status"] == "blocked"
    assert report["review_entries"]
