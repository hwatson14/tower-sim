import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.loaders.tournament_bc_selection import enumerate_tournament_bc_sets  # noqa: E402


def test_copper_has_only_more_bosses() -> None:
    available = {"more_bosses", "death_defy_down", "energy_shields_down", "foo"}
    result = enumerate_tournament_bc_sets(league="copper", available_bc_ids=available)
    assert result == [("more_bosses",)]


def test_platinum_includes_dd_or_es_and_random_pool() -> None:
    available = {
        "more_bosses",
        "death_defy_down",
        "energy_shields_down",
        "pool_a",
        "pool_b",
        "pool_c",
    }
    result = enumerate_tournament_bc_sets(league="platinum", available_bc_ids=available)
    assert len(result) == 2
    assert ("death_defy_down", "more_bosses", "pool_a", "pool_b", "pool_c") in result
    assert (
        "energy_shields_down",
        "more_bosses",
        "pool_a",
        "pool_b",
        "pool_c",
    ) in result


def test_missing_required_bc_raises() -> None:
    available = {"pool_a", "pool_b"}
    with pytest.raises(ValueError, match="more_bosses"):
        enumerate_tournament_bc_sets(league="silver", available_bc_ids=available)
