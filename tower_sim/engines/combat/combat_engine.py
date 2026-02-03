from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from tower_sim.libs.wave_damage_strict import EnemyWaveDamageLib


class CombatDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class CombatContext:
    wave: int
    enemy_hp: float
    enemy_attack: float
    is_boss: bool
    stats: Dict[str, float]
    params: Dict[str, Any]


def require(params: Dict[str, Any], *keys: str) -> None:
    for key in keys:
        if key not in params:
            raise CombatDataError(f"Missing combat parameter: {key}")


def apply_damage_reduction(dmg: float, dr_frac: float) -> float:
    if not 0.0 <= dr_frac <= 1.0:
        raise CombatDataError(f"Invalid DR fraction: {dr_frac}")
    return dmg * (1.0 - dr_frac)


def thorns_damage(enemy_hp: float, thorns_frac: float) -> float:
    if not 0.0 <= thorns_frac <= 1.0:
        raise CombatDataError(f"Invalid thorns fraction: {thorns_frac}")
    return enemy_hp * thorns_frac


def percent_current_damage(enemy_hp: float, pc_frac: float, boss_mult: float) -> float:
    if pc_frac < 0:
        raise CombatDataError("PC fraction must be >= 0")
    return enemy_hp * pc_frac * boss_mult


def resolve_wave_damage(tier: str, wave: int) -> float:
    """Resolve enemy base attack damage from wave damage tables."""
    lib = EnemyWaveDamageLib.from_repo_tables()
    return lib.wave_damage_exact(tier, wave)


def build_context_with_wave_damage(
    *,
    tier: str,
    wave: int,
    enemy_hp: float,
    is_boss: bool,
    stats: Dict[str, float],
    params: Dict[str, Any],
) -> CombatContext:
    """Convenience helper that wires wave damage tables into combat context."""
    return CombatContext(
        wave=wave,
        enemy_hp=enemy_hp,
        enemy_attack=resolve_wave_damage(tier, wave),
        is_boss=is_boss,
        stats=stats,
        params=params,
    )


def resolve_combat(ctx: CombatContext) -> Dict[str, float]:
    params = ctx.params
    require(
        params,
        "tower_dr_frac",
        "enemy_attack_mult",
        "thorns_frac",
        "pc_frac",
        "pc_boss_mult",
    )

    enemy_attack = ctx.enemy_attack * params["enemy_attack_mult"]
    tower_damage = apply_damage_reduction(enemy_attack, params["tower_dr_frac"])

    total_damage = 0.0
    total_damage += thorns_damage(ctx.enemy_hp, params["thorns_frac"])
    total_damage += percent_current_damage(
        ctx.enemy_hp,
        params["pc_frac"],
        params["pc_boss_mult"] if ctx.is_boss else 1.0,
    )

    remaining_hp = max(0.0, ctx.enemy_hp - total_damage)

    return {
        "remaining_enemy_hp": remaining_hp,
        "tower_damage_taken": tower_damage,
    }
