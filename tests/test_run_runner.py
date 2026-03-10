from __future__ import annotations

import subprocess
from pathlib import Path
import sys

import pytest

from tower_sim.run import runner


def _ids_fixture() -> Path:
    return Path("tests/fixtures/tower-sim-data/_IDS.csv")


def _spec_fixture() -> Path:
    return Path("tests/fixtures/specs/sample_spec.yaml")


def test_runner_executes_max_wave_and_writes_artifacts() -> None:
    result = runner.run(spec_path=_spec_fixture(), ids_path=_ids_fixture())
    assert result["task"] == "MAX_WAVE"
    assert result["ok"] is True
    assert (Path("out") / "max_wave_latest.json").exists()
    assert (Path("out") / "lineage_manifest_latest.json").exists()


def test_runner_applies_yaml_overlay_patch(tmp_path: Path) -> None:
    patch_path = tmp_path / "patch.yaml"
    patch_path.write_text("scenario:\n  wave: 200\n")
    result = runner.run(spec_path=_spec_fixture(), patch_path=patch_path, ids_path=_ids_fixture())
    assert result["task"] == "MAX_WAVE"


def test_runner_requires_existing_paths() -> None:
    with pytest.raises(FileNotFoundError, match="Problem spec not found"):
        runner.run(spec_path=Path("tests/fixtures/specs/does_not_exist.yaml"), ids_path=_ids_fixture())


def test_runner_module_invocation_executes_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tower_sim.run.runner",
            "--spec",
            "tests/fixtures/specs/sample_spec.yaml",
            "--ids",
            "tests/fixtures/tower-sim-data/_IDS.csv",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Wrote out/max_wave_latest.json" in proc.stdout
