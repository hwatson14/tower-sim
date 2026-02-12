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
    # IDS workshop levels are 0-indexed for unpurchased state; level 0 means 0% chance.
    # Purchased levels then increase by +0.05% per level up to the 35.00% cap.
    if level <= 0:
        return 0.0
    chance = 0.0005 * level
    return min(max(chance, 0.0), 0.35)
