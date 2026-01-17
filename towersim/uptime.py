
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict
from .wave_time import wave_seconds, GCOMP_SECONDS_BY_RARITY

MIN_EFFECTIVE_CD = 0.1

def gcomp_sec(rarity: str) -> float:
    if rarity not in GCOMP_SECONDS_BY_RARITY:
        raise ValueError(f"Unknown rarity for GComp: {rarity}")
    return GCOMP_SECONDS_BY_RARITY[rarity]

def expected_effective_cd(base_cd: float, pkg_chance: float, ws: float, gcomp_seconds: float) -> float:
    """
    Rate-based expectation model:
      packages/sec = pkg_chance / wave_seconds
      drain_rate = 1 + packages/sec * gcomp_seconds
      effective_cd = base_cd / drain_rate
    """
    pps = pkg_chance / ws
    drain_rate = 1.0 + pps * gcomp_seconds
    eff = base_cd / drain_rate
    return max(eff, MIN_EFFECTIVE_CD)

def uptime(duration: float, count: int, effective_cd: float) -> float:
    return min((duration * max(1, int(count))) / effective_cd, 1.0)
