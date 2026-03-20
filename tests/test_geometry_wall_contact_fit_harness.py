from pathlib import Path

from engine.geometry_wall_contact_fit_harness import build_wall_contact_first_fit_harness


def test_fit_harness_builds_candidates_for_fit_ready_dataset():
    path = Path(__file__).resolve().parents[1] / "templates" / "wall_contact_measurements_fit_ready_example.json"
    report = build_wall_contact_first_fit_harness(str(path))
    assert report["status"] == "candidate_fits_built__promotion_blocked"
    assert len(report["candidates"]) >= 4
    assert report["best_candidate_family_id"]
