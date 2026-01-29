from __future__ import annotations

"""
Boss Survivability Model — Authoritative, Fail-Closed

Defines full boss combat resolution used for milestone/tournament:
- Tier BCs
- Per-wave stat composition
- Time-to-kill (TTK) vs time-to-death (TTD)

No numeric values are hardcoded.
"""

from dataclasses import dataclass
from typing import Any, Dict


class BossDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class BossStats:
    hp: float
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


def resolve_boss_fight(ctx: BossContext) -> Dict[str, float]:
    require(ctx.bc_params, "boss_hp_mult", "boss_attack_mult")
    require(ctx.combat_params, "boss_dps")

    boss_hp = ctx.boss.hp * ctx.bc_params["boss_hp_mult"]
    boss_attack = ctx.boss.attack * ctx.bc_params["boss_attack_mult"]

    # Tower death time
    incoming_dps = boss_attack / ctx.boss.attack_interval
    eff_dps = incoming_dps * (1.0 - ctx.tower.dr_frac)
    if eff_dps <= ctx.tower.regen_per_sec:
        ttd = float("inf")
    else:
        ttd = ctx.tower.shields / (eff_dps - ctx.tower.regen_per_sec)

    # Boss death time
    boss_dps_taken = ctx.combat_params["boss_dps"]
    if boss_dps_taken <= 0:
        ttk = float("inf")
    else:
        ttk = boss_hp / boss_dps_taken

    outcome = "tower_kills_boss" if ttk < ttd else "boss_kills_tower"

    return {
        "ttk_seconds": ttk,
        "ttd_seconds": ttd,
        "outcome": outcome,
    }
