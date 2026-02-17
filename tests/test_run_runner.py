from __future__ import annotations

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


def test_runner_executes_max_wave_and_writes_artifacts() -> None:
    result = runner.run(spec_path=_spec_fixture(), ids_path=_ids_fixture())
    assert result["task"] == "MAX_WAVE"
    assert result["ok"] is True
    assert (Path("out") / "max_wave_latest.json").exists()
    assert (Path("out") / "lineage_manifest_latest.json").exists()


def test_runner_applies_yaml_overlay_patch() -> None:
    patch_path = Path("tests/fixtures/specs/v1_patch_override.yaml")
    result = runner.run(spec_path=_spec_fixture(), patch_path=patch_path, ids_path=_ids_fixture())
    assert result["task"] == "MAX_WAVE"


def test_runner_requires_existing_paths() -> None:
    with pytest.raises(FileNotFoundError, match="Problem spec not found"):
        runner.run(spec_path=Path("fixtures/specs/does_not_exist.yaml"), ids_path=_ids_fixture())


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
    assert (tmp_path / "out" / "max_wave_latest.json").exists()
    assert (tmp_path / "out" / "lineage_manifest_latest.json").exists()
