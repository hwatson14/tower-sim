from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from tower_sim.audit.wiring_health_check import run_wiring_health_check
from tower_sim.registry.combat_stat_contract import (
    required_max_wave_stat_input_ids,
    stat_lineage_status_lists,
)


def _write_lineage_manifest(path: Path) -> None:
    payload = {
        "required_max_wave_stat_input_ids": list(required_max_wave_stat_input_ids()),
        "status_lists": {
            stat_id: asdict(status)
            for stat_id, status in stat_lineage_status_lists().items()
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_wiring_health_check_is_ok_without_thresholds(tmp_path: Path) -> None:
    lineage_manifest = tmp_path / "stat_lineage_manifest_latest.json"
    _write_lineage_manifest(lineage_manifest)

    result = run_wiring_health_check(
        ids_path=Path("tests/fixtures/tower-sim-data/_IDS.csv"),
        lineage_manifest_path=lineage_manifest,
    )

    assert result["status"] == "ok"
    assert result["violations"] == []
    assert result["checks"]["naming_contract"]["status"] == "ok"
    assert result["checks"]["mechanics_manifest"]["status"] == "ok"
    assert result["checks"]["lineage_summary"]["stats_total"] > 0


def test_wiring_health_check_respects_threshold_violations(tmp_path: Path) -> None:
    lineage_manifest = tmp_path / "stat_lineage_manifest_latest.json"
    _write_lineage_manifest(lineage_manifest)

    result = run_wiring_health_check(
        ids_path=Path("tests/fixtures/tower-sim-data/_IDS.csv"),
        lineage_manifest_path=lineage_manifest,
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
