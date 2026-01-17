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
    # levels are 0..699 in practice; wiki describes base at 0.05% and +0.05% per level.
    if level <= 0:
        return 0.0
    base = 0.0005
    per_level = 0.0005
    chance = base + per_level * (level - 1)
    # cap 35%
    return min(max(chance, 0.0), 0.35)
