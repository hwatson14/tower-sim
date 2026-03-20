import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.loaders.tournament_bc_selection import enumerate_tournament_bc_sets  # noqa: E402


def test_champion_enumerates_4_random_plus_dd_es_plus_fixed() -> None:
    available = {
        "more_bosses:",
        "death_defy_down:",
        "energy_shields_down:",
        "pool_a:",
        "pool_b:",
        "pool_c:",
        "pool_d:",
    }
    result = enumerate_tournament_bc_sets("champion", available_bc_ids=available)
    assert len(result) == 2
    assert ("death_defy_down:", "more_bosses:", "pool_a:", "pool_b:", "pool_c:", "pool_d:") in result
    assert ("energy_shields_down:", "more_bosses:", "pool_a:", "pool_b:", "pool_c:", "pool_d:") in result


def test_legend_enumerates_5_random_plus_dd_es_plus_fixed() -> None:
    available = {
        "more_bosses:",
        "death_defy_down:",
        "energy_shields_down:",
        "pool_a:",
        "pool_b:",
        "pool_c:",
        "pool_d:",
        "pool_e:",
    }
    result = enumerate_tournament_bc_sets("legend", available_bc_ids=available)
    assert len(result) == 2
    assert (
        "death_defy_down:",
        "more_bosses:",
        "pool_a:",
        "pool_b:",
        "pool_c:",
        "pool_d:",
        "pool_e:",
    ) in result


def test_missing_more_bosses_raises() -> None:
    with pytest.raises(ValueError, match="more_bosses"):
        enumerate_tournament_bc_sets(
            "champion",
            available_bc_ids={"death_defy_down:", "energy_shields_down:", "pool_a:", "pool_b:", "pool_c:", "pool_d:"},
        )


def test_missing_dd_or_es_raises() -> None:
    with pytest.raises(ValueError, match="dd/es"):
        enumerate_tournament_bc_sets(
            "champion",
            available_bc_ids={"more_bosses:", "death_defy_down:", "pool_a:", "pool_b:", "pool_c:", "pool_d:"},
        )


def test_random_pool_too_small_raises() -> None:
    with pytest.raises(ValueError, match="Random BC pool too small"):
        enumerate_tournament_bc_sets(
            "legend",
            available_bc_ids={"more_bosses:", "death_defy_down:", "energy_shields_down:", "pool_a:", "pool_b:", "pool_c:"},
        )
