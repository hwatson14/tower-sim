import sys
from pathlib import Path

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.run.context import RunContext  # noqa: E402
from tower_sim.loaders.tier_battle_conditions import load_tier_battle_conditions  # noqa: E402
from tower_sim.engines.tier_rules import build_tier_rules  # noqa: E402


def _load_catalog():
    path = Path("reference/step1_dump_docs/part2_data/tier14_21_battle_conditions.csv")
    return load_tier_battle_conditions(path, allow_incomplete=True)


def test_build_tier_rules_requires_conditions() -> None:
    catalog = _load_catalog()
    context = RunContext.from_mode("tier")

    with pytest.raises(ValueError):
        build_tier_rules(1, context, catalog)


def test_build_tier_rules_returns_conditions() -> None:
    catalog = _load_catalog()
    context = RunContext.from_mode("tier")

    result = build_tier_rules(14, context, catalog)

    assert result.conditions
    assert result.tier == 14
