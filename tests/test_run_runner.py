from __future__ import annotations

import subprocess
from pathlib import Path
import sys

import pytest

from tower_sim.run import runner


def test_runner_fixture_result_shape() -> None:
    result = runner.run()
    assert result["evaluator"] == "max_wave"
    assert "fail_closed" in result
    assert isinstance(result.get("missing"), list)


def test_runner_requires_explicit_paths_when_fixture_defaults_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "_resolve_default_fixture_paths",
        lambda: (_missing("_IDS.csv"), _missing("sample_spec.yaml")),
    )
    with pytest.raises(FileNotFoundError, match="IDS CSV not found"):
        runner.run()


def test_runner_accepts_explicit_paths() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ids_path = repo_root / "tests" / "fixtures" / "tower-sim-data" / "_IDS.csv"
    spec_path = repo_root / "tests" / "fixtures" / "specs" / "sample_spec.yaml"
    result = runner.run(ids_path=ids_path, spec_path=spec_path)
    assert result["evaluator"] == "max_wave"


def test_runner_script_mode_executes_from_repo_root() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "tower_sim" / "run" / "runner.py"
    proc = subprocess.run(
        [sys.executable, str(script_path), "--strict"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Wrote" in proc.stdout


def _missing(name: str) -> Path:
    return Path("/tmp") / f"missing-{name}"
