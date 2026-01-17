"""Formula-backed Lab tables (exact).

Rule: only include a formula here if it exactly matches the wiki value table.
Otherwise, rely on cached CSVs scraped from the wiki.

All returned values are normalized to a *fraction* where appropriate:
- For "%"-style labs where the wiki shows "2.00" meaning "2%", we return 0.02.
- For multiplier labs where wiki shows "1.10x", we return 1.10.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Tuple


@dataclass(frozen=True)
class FormulaLab:
    unit: str  # "mult" | "fraction"
    fn: Callable[[int], float]
    raw_fmt: Callable[[int], str]


def _assert_level(level: int) -> int:
    if level < 0:
        raise ValueError("level must be >= 0")
    return level


def _percent_value_to_fraction(percent_value: float) -> float:
    # percent_value is in "percent", e.g. 2.0 means 2%
    return percent_value / 100.0


# --- Specific labs (verified on wiki) ----------------------------------------

def lab_enemy_attack_level_skip(level: int) -> float:
    """
    Enemy Attack Level Skip lab.
    Wiki Value column: 0.10, 0.20, ... , 2.00 (== 2%).
    Source: https://the-tower-idle-tower-defense.fandom.com/wiki/Lab/Enemy_Attack_Level_Skip
    """
    lvl = _assert_level(level)
    return _percent_value_to_fraction(0.10 * lvl)


def lab_enemy_health_level_skip(level: int) -> float:
    """
    Enemy Health Level Skip lab.
    Wiki Value column: 0.10, 0.20, ... , 2.00 (== 2%).
    Source: https://the-tower-idle-tower-defense.fandom.com/wiki/Lab/Enemy_Health_Level_Skip
    """
    lvl = _assert_level(level)
    return _percent_value_to_fraction(0.10 * lvl)


def lab_standard_perk_bonus(level: int) -> float:
    """
    Standard Perk Bonus lab.
    Wiki Value column: 1%, 2%, ... (25 levels).
    Source: https://the-tower-idle-tower-defense.fandom.com/wiki/Perk_Labs/Standard_Perk_Bonus
    """
    lvl = _assert_level(level)
    return _percent_value_to_fraction(1.0 * lvl)


def wall_lab_wall_regen_percent(level: int) -> float:
    """
    Wall Regen wall lab.
    Wiki Value column: 10%, 20%, ... , 300% (30 levels).
    Value is "% of tower Health Regen".
    Source: https://the-tower-idle-tower-defense.fandom.com/wiki/Wall_Labs/Wall_Regen
    """
    lvl = _assert_level(level)
    return _percent_value_to_fraction(10.0 * lvl)


def wall_lab_wall_regen_raw(level: int) -> str:
    return f"{10.0*level:.0f}%"


def _eals_raw(level:int)->str:
    return f"{0.10*level:.2f}%"

def _spb_raw(level:int)->str:
    return f"{1.0*level:.0f}%"


FORMULA_LABS: Dict[str, FormulaLab] = {
    # Names must match the IDs/lab naming convention used in your _IDS parser.

    "Enemy Attack Level Skip": FormulaLab(unit="fraction", fn=lab_enemy_attack_level_skip, raw_fmt=_eals_raw),
    "Enemy Health Level Skip": FormulaLab(unit="fraction", fn=lab_enemy_health_level_skip, raw_fmt=_eals_raw),

    "Standard Perk Bonus": FormulaLab(unit="fraction", fn=lab_standard_perk_bonus, raw_fmt=_spb_raw),

    # Wall labs (kept here because the value table is strictly linear).
    "Wall Regen": FormulaLab(unit="fraction", fn=wall_lab_wall_regen_percent, raw_fmt=wall_lab_wall_regen_raw),
}


def has_formula(lab_name: str) -> bool:
    return lab_name in FORMULA_LABS


def eval_formula(lab_name: str, level: int) -> Tuple[float, str, str]:
    fl = FORMULA_LABS[lab_name]
    return fl.fn(level), fl.raw_fmt(level), fl.unit
