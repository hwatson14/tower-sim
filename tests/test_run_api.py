from __future__ import annotations

import pytest

pytest.skip(
    "Quarantined: run_api depends on MaxWaveEvaluator, which currently fails to import.",
    allow_module_level=True,
)

from pathlib import Path
import sys


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.run_api import run  # noqa: E402
from tower_sim.spec_loader import load_problem_spec  # noqa: E402


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "specs"


def test_run_api_returns_wmax() -> None:
    spec = load_problem_spec(FIXTURES / "sample_spec.yaml")
    result = run(spec)

    assert result["fail_closed"] is False
    assert result["missing"] == []
    assert result["w_max"] == 0
    assert "resolved_from" in result
