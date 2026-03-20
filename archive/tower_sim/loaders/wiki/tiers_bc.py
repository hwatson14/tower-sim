"""
Tier battle conditions helpers relevant to skip modification.

Source: https://the-tower-idle-tower-defense.fandom.com/wiki/Tiers

The Tiers page lists two relevant BC patterns:
- "Skip Reduction - Multiply": multiply EHLS/EALS by x[VAL]
- "Skip Reduction - Subtract" (Normal tiers only): subtract X percentage points from EHLS/EALS

We model:
- multiply: chance *= mult
- subtract: chance = max(0, chance - subtract_pp)

Note: subtract is percentage points, not relative percent.
"""
from __future__ import annotations

def apply_skip_reduction_multiply(chance: float, mult: float) -> float:
    return max(0.0, chance * mult)

def apply_skip_reduction_subtract(chance: float, subtract_pp: float) -> float:
    # subtract_pp is e.g. 0.025 for -2.5pp
    return max(0.0, chance - subtract_pp)
