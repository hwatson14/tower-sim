"""Assist Module Labs (wiki) - level table.

Source: The Tower - Idle Tower Defense Wiki (Fandom), Assist Module Labs page.

The page lists 30 levels; each level grants +1% to the Assist Module Main Effect / Substat Labs.

We encode the Value column as a percent (e.g., level 10 -> 10.0).

Note: The wiki page title implies *two* labs (main effect vs substat).
In TowerSim we treat them as two separate lab tracks that share the same value ladder,
unless the user's IDS data indicates otherwise.

"""

from __future__ import annotations

from dataclasses import dataclass

MAX_LEVEL = 30

def value_percent(level: int) -> float:
    """Return the wiki 'Value' for a given level, in percent points.

    level: 0..30 (0 means not researched)
    """
    if level < 0:
        raise ValueError("level must be >= 0")
    if level == 0:
        return 0.0
    if level > MAX_LEVEL:
        # clamp rather than explode; the simulator should remain usable if wiki extends
        level = MAX_LEVEL
    return float(level)  # 1% per level up to 30%

@dataclass(frozen=True)
class AssistLabLevels:
    """Two lab tracks (bonus/main-effect vs substat)."""
    bonus_level: int  # main effect / bonus lab
    substat_level: int  # substat efficiency lab

    @property
    def bonus_percent(self) -> float:
        return value_percent(self.bonus_level)

    @property
    def substat_percent(self) -> float:
        return value_percent(self.substat_level)
