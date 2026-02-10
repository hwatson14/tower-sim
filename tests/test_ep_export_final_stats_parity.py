from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.audit.ep_export_final_stats_parity import verify_final_stats_against_ep_export


def _ids_path() -> Path:
    return Path("tests/fixtures/tower-sim-data/_IDS.csv")


def _spec_path(name: str) -> Path:
    return Path("tests/fixtures/specs") / name


def test_verify_final_stats_enforces_preset_mapping() -> None:
    with pytest.raises(ValueError, match="Preset mismatch"):
        verify_final_stats_against_ep_export(
            ids_path=_ids_path(),
            spec_path=_spec_path("tournament_champion_spec.yaml"),
            suite="ehp",
        )


def test_verify_final_stats_returns_comparison_report() -> None:
    report = verify_final_stats_against_ep_export(
        ids_path=_ids_path(),
        spec_path=_spec_path("sample_spec.yaml"),
        suite="ehp",
    )

    assert report["preset"] == "farming"
    assert report["spec_mode"] == "farming"
    assert report["matched_count"] + report["mismatch_count"] == len(report["compared_rows"])
    assert len(report["compared_rows"]) > 0
