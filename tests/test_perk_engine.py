from __future__ import annotations

from pathlib import Path
import sys

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.perk_engine import (  # noqa: E402
    InvalidPerkError,
    PerkEngine,
    PerkInput,
    PerkMode,
)
from tower_sim.run_context import PerksDisabledError, RunContext  # noqa: E402


def test_perk_engine_applies_multiplicative() -> None:
    engine = PerkEngine()
    context = RunContext.farming(tier="T1")
    perks = [
        PerkInput(
            name="Test Perk",
            perk_base=0.2,
            quantity=2,
            standard_perk_bonus=0.25,
            mode=PerkMode.MULTIPLICATIVE,
            provenance="wiki:perks",
        )
    ]

    results = engine.apply(context, perks)

    assert results["Test Perk"].value == 1.75


def test_perk_engine_blocks_perks_in_tournament() -> None:
    engine = PerkEngine()
    context = RunContext.tournament(tier="T1")
    perks = [
        PerkInput(
            name="Test Perk",
            perk_base=0.2,
            quantity=1,
            standard_perk_bonus=0.0,
            mode=PerkMode.ADDITIVE,
            provenance="wiki:perks",
        )
    ]

    with pytest.raises(PerksDisabledError):
        engine.apply(context, perks)


def test_perk_engine_requires_provenance() -> None:
    engine = PerkEngine()
    context = RunContext.farming(tier="T1")
    perks = [
        PerkInput(
            name="Test Perk",
            perk_base=0.2,
            quantity=1,
            standard_perk_bonus=0.0,
            mode=PerkMode.ADDITIVE,
            provenance="",
        )
    ]

    with pytest.raises(InvalidPerkError):
        engine.apply(context, perks)
