from __future__ import annotations

from pathlib import Path
import sys


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.run_api import run  # noqa: E402
from tower_sim.spec_loader import load_problem_spec  # noqa: E402


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "specs"


def test_run_api_fail_closed_with_missing_mechanics() -> None:
    spec = load_problem_spec(FIXTURES / "sample_spec.yaml")
    result = run(spec)

    assert result["fail_closed"] is True
    assert result["missing"] == [
        "boss_combat_inputs",
        "tier_battle_conditions_unsupported",
    ]
    assert result["w_max"] is None
    assert "resolved_from" in result
