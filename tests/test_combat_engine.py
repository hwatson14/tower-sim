from __future__ import annotations

from pathlib import Path
import sys

import pytest


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.combat.combat_engine import (  # noqa: E402
    CombatContext,
    CombatDataError,
    apply_damage_reduction,
    percent_current_damage,
    resolve_combat,
    thorns_damage,
)


def test_apply_damage_reduction_bounds() -> None:
    with pytest.raises(CombatDataError):
        apply_damage_reduction(100.0, -0.1)
    with pytest.raises(CombatDataError):
        apply_damage_reduction(100.0, 1.1)


def test_thorns_damage_bounds() -> None:
    with pytest.raises(CombatDataError):
        thorns_damage(100.0, -0.1)
    with pytest.raises(CombatDataError):
        thorns_damage(100.0, 1.1)


def test_percent_current_damage_bounds() -> None:
    with pytest.raises(CombatDataError):
        percent_current_damage(100.0, -0.01, 1.0)


def test_resolve_combat_requires_parameters() -> None:
    ctx = CombatContext(
        wave=1,
        enemy_hp=100.0,
        enemy_attack=10.0,
        is_boss=False,
        stats={},
        params={},
    )

    with pytest.raises(CombatDataError):
        resolve_combat(ctx)


def test_resolve_combat_applies_damage_and_reduction() -> None:
    ctx = CombatContext(
        wave=10,
        enemy_hp=1_000.0,
        enemy_attack=200.0,
        is_boss=False,
        stats={},
        params={
            "tower_dr_frac": 0.25,
            "enemy_attack_mult": 1.0,
            "thorns_frac": 0.1,
            "pc_frac": 0.2,
            "pc_boss_mult": 0.5,
        },
    )

    result = resolve_combat(ctx)

    assert result["tower_damage_taken"] == 150.0
    assert result["remaining_enemy_hp"] == 700.0


def test_resolve_combat_uses_boss_multiplier() -> None:
    ctx = CombatContext(
        wave=10,
        enemy_hp=1_000.0,
        enemy_attack=100.0,
        is_boss=True,
        stats={},
        params={
            "tower_dr_frac": 0.0,
            "enemy_attack_mult": 2.0,
            "thorns_frac": 0.0,
            "pc_frac": 0.1,
            "pc_boss_mult": 0.5,
        },
    )

    result = resolve_combat(ctx)

    assert result["tower_damage_taken"] == 200.0
    assert result["remaining_enemy_hp"] == 950.0
