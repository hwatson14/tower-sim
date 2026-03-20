"""
TowerSim - Wiki-derived rules (authoritative where cited).

Sources:
- Modules page (substat slots unlocked at levels 41/101/141/161/201/241): https://the-tower-idle-tower-defense.fandom.com/wiki/Modules
- Sub-Module Effects page (hard caps list note): https://the-tower-idle-tower-defense.fandom.com/wiki/Sub-Module_Effects
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

# Sub-module effect slot unlock thresholds (inclusive)
# "Leveling up modules to levels 41, 101, 141, 161, 201, and 241 unlock additional slots..."
SUBSTAT_SLOT_UNLOCK_LEVELS: List[int] = [41, 101, 141, 161, 201, 241]

def max_active_substats_for_module_level(level: int) -> int:
    """
    Wiki rule: modules have 2 substat slots by default; +1 slot unlocked at each threshold level.
    """
    if level < 1:
        return 0
    base_slots = 2
    extra = sum(1 for t in SUBSTAT_SLOT_UNLOCK_LEVELS if level >= t)
    return base_slots + extra

# Hard caps mentioned on the Sub-Module Effects page note.
# These are caps on FINAL effective stats, even with assist substats.
HARD_CAPS = {
    "Defense %": 0.98,            # 98%
    "Chrono Field Speed Reduction": 0.90,  # 90% slow cap
    "Wall Rebuild (seconds)": 150.0,       # minimum rebuild time? (wiki note says 150s Wall rebuild cap)
    "Shockwave Frequency (seconds)": 7.0,  # min frequency
    "Death Defy": 0.40,           # 40%
    "Inner Land Mine Cooldown (seconds)": 37.0,  # min CD
}

def apply_hard_cap(stat_key: str, value: float) -> float:
    cap = HARD_CAPS.get(stat_key)
    if cap is None:
        return value
    # For percent caps, cap is max value; for seconds caps, these are minimums (smaller is "better")
    if "seconds" in stat_key.lower():
        return max(value, cap)
    return min(value, cap)
