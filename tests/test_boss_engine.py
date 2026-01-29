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
        pc_frac=None,
        pc_boss_mult=None,
        package_chance=None,
        package_heal=None,
        damage_reduction=None,
        provenance="",
    )

    with pytest.raises(MissingMechanicError):
        engine.evaluate(inputs)


def test_boss_engine_returns_minimal_survivability() -> None:
    engine = BossCombatEngine()
    inputs = BossCombatInputs(
        wave=100,
        wave_damage=1_000.0,
        tower_hp=10_000.0,
        tower_regen=100.0,
        defense_pct=0.2,
        thorns_pct=0.1,
        pc_frac=0.2,
        pc_boss_mult=1.5,
        package_chance=0.05,
        package_heal=0.2,
        damage_reduction=0.1,
        provenance="sheet:boss_model",
    )

    result = engine.evaluate(inputs)
    assert result.effective_damage_per_sec == pytest.approx(720.0)
    assert result.effective_regen_per_sec == pytest.approx(100.01)
    assert result.net_damage_per_sec == pytest.approx(619.99)
    assert result.time_to_death_sec == pytest.approx(10_000.0 / 619.99)
    assert result.boss_hp_frac_damage_per_hit == pytest.approx(0.4)
