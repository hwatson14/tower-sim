from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
import sys

import pytest

from tower_sim.run import runner


def _ids_fixture() -> Path:
    return Path("tests/fixtures/tower-sim-data/_IDS.csv")


def _spec_fixture() -> Path:
    return Path("fixtures/specs/max_wave.yaml")


def test_runner_executes_max_wave_and_writes_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    spec_path = (repo_root / "fixtures/specs/max_wave.yaml").resolve()
    ids_path = (repo_root / "tests/fixtures/tower-sim-data/_IDS.csv").resolve()

    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir(parents=True, exist_ok=True)

    result = runner.run(spec_path=spec_path, ids_path=ids_path)
    assert result["task"] == "MAX_WAVE"
    assert result["ok"] is True
    assert (tmp_path / "out" / "max_wave_runner/max_wave_latest.json").exists()
    assert (tmp_path / "out" / "max_wave_runner/runner_output_latest.json").exists()


def test_runner_applies_yaml_overlay_patch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    spec_path = (repo_root / "fixtures/specs/max_wave.yaml").resolve()
    ids_path = (repo_root / "tests/fixtures/tower-sim-data/_IDS.csv").resolve()
    patch_path = (repo_root / "tests/fixtures/specs/v1_patch_override.yaml").resolve()

    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir(parents=True, exist_ok=True)

    result = runner.run(spec_path=spec_path, patch_path=patch_path, ids_path=ids_path)
    assert result["task"] == "MAX_WAVE"
    assert (tmp_path / "out" / "max_wave_runner/max_wave_latest.json").exists()
    assert (tmp_path / "out" / "max_wave_runner/runner_output_latest.json").exists()


def test_runner_requires_existing_paths() -> None:
    with pytest.raises(FileNotFoundError, match="Problem spec not found"):
        runner.run(spec_path=Path("fixtures/specs/does_not_exist.yaml"), ids_path=_ids_fixture())
    with pytest.raises(FileNotFoundError, match="IDS snapshot not found"):
        runner.run(
            spec_path=_spec_fixture(),
            ids_path=Path("tests/fixtures/tower-sim-data/does_not_exist.csv"),
        )


def test_runner_module_mode_writes_outputs_under_cwd(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    spec_path = (repo_root / "fixtures/specs/max_wave.yaml").resolve()
    ids_path = (repo_root / "tests/fixtures/tower-sim-data/_IDS.csv").resolve()
    env = dict(os.environ)
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(repo_root) if not pythonpath else f"{repo_root}:{pythonpath}"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tower_sim.run",
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
    assert (tmp_path / "out" / "max_wave_runner/max_wave_latest.json").exists()
    assert (tmp_path / "out" / "max_wave_runner/runner_output_latest.json").exists()
    assert "SUMMARY w_max=" in proc.stdout


def test_runner_module_mode_accepts_legacy_max_wave_task_arg(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    spec_path = (repo_root / "fixtures/specs/max_wave.yaml").resolve()
    ids_path = (repo_root / "tests/fixtures/tower-sim-data/_IDS.csv").resolve()
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


def test_runner_output_contains_max_wave_search_contract_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    spec_path = (repo_root / "fixtures/specs/max_wave.yaml").resolve()
    ids_path = (repo_root / "tests/fixtures/tower-sim-data/_IDS.csv").resolve()

    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir(parents=True, exist_ok=True)

    result = runner.run(spec_path=spec_path, ids_path=ids_path)
    assert result["ok"] is True

    max_wave_path = tmp_path / "out" / "max_wave_runner" / "max_wave_latest.json"
    payload = json.loads(max_wave_path.read_text(encoding="utf-8"))

    assert payload["w_max"] is not None
    assert payload["fail_closed"] is False
    assert payload["missing"] == []
    assert payload["override_collisions"] == []
    assert payload["failure_wave"] is not None
    assert payload["failure_reason"] in {"boss_kills_tower", "tower_kills_boss"}

    diagnostics = payload["diagnostics"]
    assert "w_max_search" in diagnostics
    assert "margin_trace" in diagnostics
    assert "boss_survivability" in diagnostics

    search = diagnostics["w_max_search"]
    assert payload["w_max"] <= search["max_wave"]
    assert search["search_strategy"] == "exponential_binary"
    assert isinstance(search["last_wave_result"], dict)

    trace = diagnostics["margin_trace"]
    assert isinstance(trace, list)
    assert len(trace) > 0
    assert {"wave", "outcome", "ttk_seconds", "ttd_seconds", "margin_seconds"}.issubset(trace[0])



def test_runner_output_enforces_decisive_stat_wiring_diagnostics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    spec_path = (repo_root / "fixtures/specs/max_wave.yaml").resolve()
    ids_path = (repo_root / "tests/fixtures/tower-sim-data/_IDS.csv").resolve()

    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir(parents=True, exist_ok=True)

    runner.run(spec_path=spec_path, ids_path=ids_path)

    max_wave_path = tmp_path / "out" / "max_wave_runner" / "max_wave_latest.json"
    payload = json.loads(max_wave_path.read_text(encoding="utf-8"))
    diagnostics = payload["diagnostics"]

    decisive_ids = (
        "tower_hp",
        "tower_regen",
        "def_pct",
        "wall_hp",
        "wall_regen",
        "thorns_damage_mult",
    )
    observed = diagnostics["observed_contributors_by_stat_input_id"]
    for stat_id in decisive_ids:
        assert stat_id in observed
        assert isinstance(observed[stat_id], list)
        assert len(observed[stat_id]) > 0

    assert "uw_black_hole_cooldown" in observed
    assert "uw" in observed["uw_black_hole_cooldown"]

    scenario_wave_sources = diagnostics["combat_snapshot_sources_scenario_wave"]
    for stat_id in decisive_ids:
        assert scenario_wave_sources[stat_id] == ["at_wave_snapshot"]

    timing = diagnostics["timing_uptime"]
    assert "uw_interval_counts" in timing
    assert "black_hole" in timing["uw_interval_counts"]
    assert timing["uw_interval_counts"]["black_hole"] >= 0
