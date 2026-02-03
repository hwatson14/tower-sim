from __future__ import annotations

from pathlib import Path
import sys

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.run.problem_spec import ProblemSpec  # noqa: E402
from tower_sim.run.spec_loader import load_problem_spec  # noqa: E402


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "specs"


def test_loads_yaml_spec() -> None:
    spec = load_problem_spec(FIXTURES / "sample_spec.yaml")
    assert isinstance(spec, ProblemSpec)
    assert spec.scenario.mode == "farming"
    assert spec.scenario.tier == 14
    assert spec.scenario.wave == 100
    assert len(spec.stat_inputs) == 12


def test_loads_json_spec() -> None:
    spec = load_problem_spec(FIXTURES / "sample_spec.json")
    assert spec.scenario.mode == "farming"
    assert spec.scenario.tier == 14
    assert spec.stat_inputs[0].stat_id == "tower_hp"


def test_unknown_keys_fail_closed(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        """
scenario:
  mode: farming
  tier: 14
stat_inputs: []
extra: 1
"""
    )
    with pytest.raises(ValueError, match="Unknown keys"):
        load_problem_spec(bad)
