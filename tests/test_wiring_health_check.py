from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from tower_sim.audit.wiring_health_check import (
    _LEGACY_DEFAULT_LINEAGE_MANIFEST,
    _RUNNER_LINEAGE_MANIFEST,
    _resolve_lineage_manifest_path,
    run_wiring_health_check,
)
from tower_sim.registry.combat_stat_contract import (
    required_max_wave_stat_input_ids,
    stat_lineage_status_lists,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ids_path() -> Path:
    return (_repo_root() / "tests/fixtures/tower-sim-data/_IDS.csv").resolve()


def _run_blessed_max_wave(tmp_path: Path) -> None:
    repo_root = _repo_root()
    spec_path = (repo_root / "fixtures/specs/max_wave.yaml").resolve()
    ids_path = _ids_path()
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(repo_root) if not pythonpath else f"{repo_root}:{pythonpath}"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tower_sim.run",
            "MAX_WAVE",
            "--spec",
            str(spec_path),
            "--ids",
            str(ids_path),
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def _write_stat_lineage_manifest(path: Path) -> None:
    payload = {
        "required_max_wave_stat_input_ids": list(required_max_wave_stat_input_ids()),
        "status_lists": {
            stat_id: asdict(status)
            for stat_id, status in stat_lineage_status_lists().items()
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_wiring_health_check_is_ok_without_thresholds(tmp_path: Path) -> None:
    _run_blessed_max_wave(tmp_path)
    lineage_manifest = tmp_path / "out" / "stat_lineage_manifest_latest.json"
    _write_stat_lineage_manifest(lineage_manifest)

    result = run_wiring_health_check(
        ids_path=_ids_path(),
        lineage_manifest_path=lineage_manifest,
    )

    assert result["status"] == "ok"
    assert result["violations"] == []
    assert result["checks"]["naming_contract"]["status"] == "ok"
    assert result["checks"]["mechanics_manifest"]["status"] == "ok"
    assert result["checks"]["lineage_summary"]["stats_total"] > 0


def test_wiring_health_check_respects_threshold_violations(tmp_path: Path) -> None:
    _run_blessed_max_wave(tmp_path)
    lineage_manifest = tmp_path / "out" / "stat_lineage_manifest_latest.json"
    _write_stat_lineage_manifest(lineage_manifest)

    result = run_wiring_health_check(
        ids_path=_ids_path(),
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
            ids_path=_ids_path(),
            lineage_manifest_path=invalid_manifest,
        )
    except ValueError as exc:
        assert "required_max_wave_stat_input_ids" in str(exc)
    else:
        raise AssertionError("Expected fail-closed ValueError for invalid lineage manifest")


def test_resolve_lineage_manifest_path_falls_back_to_runner_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    runner_manifest = out_dir / "lineage_manifest_latest.json"
    runner_manifest.write_text("{}", encoding="utf-8")

    resolved = _resolve_lineage_manifest_path(_LEGACY_DEFAULT_LINEAGE_MANIFEST)

    assert resolved == _RUNNER_LINEAGE_MANIFEST


def test_resolve_lineage_manifest_path_preserves_explicit_missing_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    explicit_path = Path("out/custom_manifest.json")

    resolved = _resolve_lineage_manifest_path(explicit_path)

    assert resolved == explicit_path
