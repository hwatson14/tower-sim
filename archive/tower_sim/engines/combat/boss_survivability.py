from __future__ import annotations

"""
Boss Survivability Model — Authoritative, Fail-Closed

Defines full boss combat resolution used for milestone/tournament:
- Tier BCs
- Per-wave stat composition
- Time-to-kill (TTK) vs time-to-death (TTD)

v1 note: boss survival uses percent-based boss damage sources only and does not
require boss HP values (TTK is derived from fractional damage per hit). Heat-up
rate is specified by v1 requirements.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict


class BossDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class BossStats:
    hp: float | None
    attack: float
    attack_interval: float
    enrage_mult: float


@dataclass(frozen=True)
class TowerDefense:
    dr_frac: float
    regen_per_sec: float
    shields: float


@dataclass(frozen=True)
class BossContext:
    wave: int
    tier: int
    league: str
    boss: BossStats
    tower: TowerDefense
    combat_params: Dict[str, Any]
    bc_params: Dict[str, Any]


def require(d: Dict[str, Any], *keys: str) -> None:
    for k in keys:
        if k not in d:
            raise BossDataError(f"Missing boss parameter: {k}")


HEAT_UP_PER_HIT = 0.04  # Provenance: v1 requirement (boss hit damage +4% each hit).


def resolve_boss_fight(ctx: BossContext) -> Dict[str, float]:
    require(
        ctx.combat_params,
        "tower_hp",
        "tower_regen",
        "defense_pct",
        "defense_abs",
        "wall_hp",
        "wall_regen",
        "damage_reduction",
        "thorns_frac",
        "pc_frac",
        "pc_boss_mult",
        "orb_damage_frac",
        "electrons_damage_frac",
    )

    boss_attack = ctx.boss.attack
    if boss_attack < 0:
        raise BossDataError(f"Boss attack must be >= 0, got {boss_attack}")
    hit_interval = ctx.boss.attack_interval
    if hit_interval <= 0:
        raise BossDataError(f"Boss hit interval must be > 0, got {hit_interval}")

    tower_hp = float(ctx.combat_params["tower_hp"])
    tower_regen = float(ctx.combat_params["tower_regen"])
    defense_pct = float(ctx.combat_params["defense_pct"])
    defense_abs = float(ctx.combat_params["defense_abs"])
    wall_hp = float(ctx.combat_params["wall_hp"])
    wall_regen = float(ctx.combat_params["wall_regen"])
    damage_reduction = float(ctx.combat_params["damage_reduction"])

    thorns_frac = float(ctx.combat_params["thorns_frac"])
    pc_frac = float(ctx.combat_params["pc_frac"])
    pc_boss_mult = float(ctx.combat_params["pc_boss_mult"])
    orb_damage_frac = float(ctx.combat_params["orb_damage_frac"])
    electrons_damage_frac = float(ctx.combat_params["electrons_damage_frac"])

    _validate_fraction("defense_pct", defense_pct)
    _validate_fraction("damage_reduction", damage_reduction)
    _validate_fraction("thorns_frac", thorns_frac)
    _validate_fraction("pc_frac", pc_frac)
    _validate_fraction("orb_damage_frac", orb_damage_frac)
    _validate_fraction("electrons_damage_frac", electrons_damage_frac)
    _validate_non_negative("pc_boss_mult", pc_boss_mult)
    if defense_abs < 0:
        raise BossDataError(f"defense_abs must be >= 0, got {defense_abs}")
    if tower_hp < 0 or wall_hp < 0:
        raise BossDataError("tower_hp and wall_hp must be >= 0")
    if tower_regen < 0 or wall_regen < 0:
        raise BossDataError("tower_regen and wall_regen must be >= 0")

    # Boss death time.
    # Plasma Cannon is applied immediately on boss spawn; thorns and other
    # percent damage trigger per boss hit.
    immediate_pc_frac = pc_frac * pc_boss_mult
    remaining_hp_frac = max(0.0, 1.0 - immediate_pc_frac)
    per_hit_boss_frac = thorns_frac + orb_damage_frac + electrons_damage_frac
    if remaining_hp_frac <= 0:
        ttk = 0.0
        hits_to_kill = 0
    elif per_hit_boss_frac <= 0:
        ttk = float("inf")
        hits_to_kill = math.inf
    else:
        hits_to_kill = math.ceil(remaining_hp_frac / per_hit_boss_frac)
        ttk = hits_to_kill * hit_interval

    # Tower death time with heat-up (+4% per hit).
    ttd, hits_to_death = _time_to_death(
        boss_attack=boss_attack,
        hit_interval=hit_interval,
        tower_hp=tower_hp,
        tower_regen=tower_regen,
        defense_pct=defense_pct,
        defense_abs=defense_abs,
        wall_hp=wall_hp,
        wall_regen=wall_regen,
        damage_reduction=damage_reduction,
    )

    outcome = "tower_kills_boss" if ttk < ttd else "boss_kills_tower"

    return {
        "ttk_seconds": ttk,
        "ttd_seconds": ttd,
        "outcome": outcome,
        "hits_to_kill": hits_to_kill,
        "hits_to_death": hits_to_death,
    }


def _validate_fraction(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise BossDataError(f"{name} must be in [0,1], got {value}")


def _validate_non_negative(name: str, value: float) -> None:
    if value < 0:
        raise BossDataError(f"{name} must be >= 0, got {value}")


def _time_to_death(
    *,
    boss_attack: float,
    hit_interval: float,
    tower_hp: float,
    tower_regen: float,
    defense_pct: float,
    defense_abs: float,
    wall_hp: float,
    wall_regen: float,
    damage_reduction: float,
) -> tuple[float, float]:
    if boss_attack <= 0:
        return float("inf"), math.inf

    tower_max = tower_hp
    wall_max = wall_hp
    tower_current = tower_hp
    wall_current = wall_hp

    regen_per_hit = tower_regen * hit_interval
    wall_regen_per_hit = wall_regen * hit_interval

    max_hits = 1_000_000
    for hit in range(1, max_hits + 1):
        heat_mult = 1.0 + (HEAT_UP_PER_HIT * (hit - 1))
        raw_damage = boss_attack * heat_mult
        reduced = raw_damage * (1.0 - defense_pct)
        reduced = max(0.0, reduced - defense_abs)
        reduced *= (1.0 - damage_reduction)

        damage_remaining = reduced
        if wall_current > 0:
            if damage_remaining >= wall_current:
                damage_remaining -= wall_current
                wall_current = 0.0
            else:
                wall_current -= damage_remaining
                damage_remaining = 0.0

        if damage_remaining > 0:
            tower_current -= damage_remaining

        if tower_current <= 0:
            return hit * hit_interval, float(hit)

        wall_current = min(wall_max, wall_current + wall_regen_per_hit)
        tower_current = min(tower_max, tower_current + regen_per_hit)

    return float("inf"), math.inf
