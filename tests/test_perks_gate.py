import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.perks_gate import PerksDisabledError, assert_perks_enabled  # noqa: E402
from tower_sim.run_context import RunContext  # noqa: E402


def test_perks_gate_missing_context_raises() -> None:
    with pytest.raises(PerksDisabledError, match="RunContext missing"):
        assert_perks_enabled(None)


def test_perks_gate_disabled_raises() -> None:
    with pytest.raises(PerksDisabledError, match="disabled"):
        assert_perks_enabled(RunContext.tournament("T1"))


def test_perks_gate_enabled_allows() -> None:
    assert_perks_enabled(RunContext.tournament("T1", perks_enabled=True))
