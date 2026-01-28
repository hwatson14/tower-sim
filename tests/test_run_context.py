import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.perks_gate import PerksDisabledError  # noqa: E402
from tower_sim.run_context import RunContext  # noqa: E402


@pytest.mark.parametrize("mode", ["tier", "farming", "milestone"])
def test_run_context_tier_modes_enable_perks(mode: str) -> None:
    context = RunContext.from_mode(mode)

    assert context.perks_enabled is True
    context.require_perks_enabled()


def test_run_context_tournament_disables_perks() -> None:
    context = RunContext.from_mode("tournament")

    assert context.perks_enabled is False
    with pytest.raises(PerksDisabledError):
        context.require_perks_enabled()


def test_run_context_tourney_alias_disables_perks() -> None:
    context = RunContext.from_mode("tourney")

    assert context.perks_enabled is False
    with pytest.raises(PerksDisabledError):
        context.require_perks_enabled()


def test_run_context_unknown_mode_raises() -> None:
    with pytest.raises(ValueError):
        RunContext.from_mode("unknown-mode")
