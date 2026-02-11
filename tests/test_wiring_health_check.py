from __future__ import annotations

import json
from pathlib import Path

from tower_sim.audit.wiring_health_check import run_wiring_health_check


def test_wiring_health_check_is_ok_without_thresholds() -> None:
    result = run_wiring_health_check(
        ids_path=Path("tests/fixtures/tower-sim-data/_IDS.csv"),
        lineage_manifest_path=Path("out/stat_lineage_manifest_latest.json"),
    )

    assert result["status"] == "ok"
    assert result["violations"] == []
    assert result["checks"]["naming_contract"]["status"] == "ok"
    assert result["checks"]["mechanics_manifest"]["status"] == "ok"
    assert result["checks"]["lineage_summary"]["stats_total"] > 0


def test_wiring_health_check_respects_threshold_violations() -> None:
    result = run_wiring_health_check(
        ids_path=Path("tests/fixtures/tower-sim-data/_IDS.csv"),
        lineage_manifest_path=Path("out/stat_lineage_manifest_latest.json"),
        max_required_max_wave_gaps=0,
    )

    assert result["status"] == "error"
    assert any(
        item.startswith("lineage_required_max_wave_gap_count")
        for item in result["violations"]
    )


def test_wiring_health_check_fails_closed_for_invalid_manifest(tmp_path: Path) -> None:
    invalid_manifest = tmp_path / "manifest.json"
    invalid_manifest.write_text(json.dumps({"status_lists": {}}), encoding="utf-8")

    try:
        run_wiring_health_check(
            ids_path=Path("tests/fixtures/tower-sim-data/_IDS.csv"),
            lineage_manifest_path=invalid_manifest,
        )
    except ValueError as exc:
        assert "required_max_wave_stat_input_ids" in str(exc)
    else:
        raise AssertionError("Expected fail-closed ValueError for invalid lineage manifest")
