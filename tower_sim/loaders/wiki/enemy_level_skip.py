"""
Enemy Attack/Health Level Skip (EALS/EHLS) workshop baseline.

Source: https://the-tower-idle-tower-defense.fandom.com/wiki/Enemy_Level_Skip

Key facts (wiki):
- Both workshops have 699 levels.
- Base chance 0.05%.
- Each level adds 0.05%.
- Maximum 35.00%.

We expose:
- workshop_level_to_chance(level): returns chance in [0, 0.35]
"""
from __future__ import annotations

def workshop_level_to_chance(level: int) -> float:
    # Wiki source above: base 0.05% and +0.05% per level, capped at 35.00% at level 699.
    # We model level 0 as base-only (0.05%) and level N as 0.05% * (N + 1).
    if level < 0:
        return 0.0
    chance = 0.0005 * (level + 1)
    return min(max(chance, 0.0), 0.35)
