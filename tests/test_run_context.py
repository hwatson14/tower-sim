import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.run.context import PerksDisabledError, RunContext  # noqa: E402
from tower_sim.loaders.wiki.perks import (  # noqa: E402
    apply_standard_perk_bonus_multiplicative_checked,
)


def test_run_context_defaults_perks_by_run_type() -> None:
    farm = RunContext.farming("T1")
    tourney = RunContext.tournament("T1")
    assert farm.perks_enabled is True
    assert tourney.perks_enabled is False


def test_perks_checked_fail_closed_in_tournament() -> None:
    context = RunContext.tournament("T1")
    with pytest.raises(PerksDisabledError, match="Perks are disabled"):
        apply_standard_perk_bonus_multiplicative_checked(context, 0.2, 1, 0.25)


def test_perks_checked_allows_explicit_enablement() -> None:
    context = RunContext.tournament("T1", perks_enabled=True)
    result = apply_standard_perk_bonus_multiplicative_checked(context, 0.2, 1, 0.25)
    assert result == 1.5
