from pathlib import Path

from engine.geometry_wall_contact_fit_ingestion import build_wall_contact_fit_ingestion_scaffold
from engine.geometry_wall_contact_target_surface import CANONICAL_TARGET_SURFACE


def test_fit_ingestion_scaffold_on_example_dataset():
    path = Path(__file__).resolve().parents[1] / "templates" / "wall_contact_measurements_fit_ready_example.json"
    report = build_wall_contact_fit_ingestion_scaffold(path)
    assert report["readiness"]["status"] == "fit_ready"
    assert report["canonical_target_surface"] == CANONICAL_TARGET_SURFACE
    assert len(report["valid_rows"]) == 8
