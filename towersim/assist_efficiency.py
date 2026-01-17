"""Assist-slot efficiency helpers.

Assist modules are reduced in effect when placed in an assist slot. TowerSim models 3 distinct
concepts:

1) Assist slot cap rarity: unique effects and substat roll values are capped by slot rarity.
2) Assist bonus (main effect / unique effect) efficiency: a percent of the primary effect carries over.
3) Assist substat efficiency: a percent of substat values carry over.

The stone ladders for (2) and (3) are NOT encoded here; they are read from the user's IDS.
The lab ladders are encoded via towersim.wiki.assist_module_labs.

Wiki ambiguity:
- Version history text says Main Effect, Unique Effect, and Substats are reduced by efficiency.
- User requirement in this project says Unique Effects are capped by rarity but NOT scaled by efficiencies.
  We therefore keep a switch `scale_unique_effect_by_bonus_eff` (default False).
"""

from __future__ import annotations

from dataclasses import dataclass

from .wiki.assist_module_labs import AssistLabLevels

@dataclass(frozen=True)
class AssistEfficiencyInputs:
    """Inputs for building assist efficiencies.

    stone_bonus_percent: the bonus efficiency % purchased with stones (0..30 typical)
    stone_substat_percent: the substat efficiency % purchased with stones (0..30 typical)
    labs: AssistLabLevels (bonus and substat)
    """
    stone_bonus_percent: float
    stone_substat_percent: float
    labs: AssistLabLevels

@dataclass(frozen=True)
class AssistEfficiencies:
    """Computed efficiencies as decimals (0.10 == 10%)."""
    bonus_eff: float
    substat_eff: float

def compute_efficiencies(inp: AssistEfficiencyInputs) -> AssistEfficiencies:
    """Compute final efficiencies as decimals.

    We interpret stone percent and lab percent as additive to a base 0%,
    clamped to 0..100.

    Example: stone 10% and lab 2% -> 12% -> 0.12
    """
    bonus_pct = float(inp.stone_bonus_percent) + float(inp.labs.bonus_percent)
    sub_pct = float(inp.stone_substat_percent) + float(inp.labs.substat_percent)

    bonus_pct = max(0.0, min(100.0, bonus_pct))
    sub_pct = max(0.0, min(100.0, sub_pct))

    return AssistEfficiencies(bonus_eff=bonus_pct / 100.0, substat_eff=sub_pct / 100.0)

def apply_bonus_eff_to_main_effect(main_multiplier_full: float, bonus_eff: float) -> float:
    """Apply bonus efficiency to an assist module main effect.

    Effective Paths formula (as provided by user):
    ((main_full - 1) * (1 + stone + lab) * 0.01) + 1
    where stone+lab is in percent points.

    In TowerSim we accept `bonus_eff` as a decimal (0.12).
    So: 1 + (main_full - 1) * bonus_eff
    """
    return 1.0 + (float(main_multiplier_full) - 1.0) * float(bonus_eff)
