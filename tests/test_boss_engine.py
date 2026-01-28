from __future__ import annotations

from pathlib import Path
import sys

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.combat.boss_engine import (  # noqa: E402
    BossCombatEngine,
    BossCombatInputs,
    MissingMechanicError,
)


def test_boss_engine_requires_inputs() -> None:
    engine = BossCombatEngine()
    inputs = BossCombatInputs(
        wave=0,
        wave_damage=0.0,
        tower_hp=0.0,
        tower_regen=0.0,
        defense_pct=0.0,
        thorns_pct=None,
        package_chance=None,
        package_heal=None,
        damage_reduction=None,
        provenance="",
    )

    with pytest.raises(MissingMechanicError):
        engine.evaluate(inputs)


def test_boss_engine_fail_closed_without_mechanics() -> None:
    engine = BossCombatEngine()
    inputs = BossCombatInputs(
        wave=100,
        wave_damage=1_000.0,
        tower_hp=10_000.0,
        tower_regen=100.0,
        defense_pct=0.2,
        thorns_pct=0.1,
        package_chance=0.05,
        package_heal=0.2,
        damage_reduction=0.0,
        provenance="sheet:boss_model",
    )

    with pytest.raises(MissingMechanicError):
        engine.evaluate(inputs)
