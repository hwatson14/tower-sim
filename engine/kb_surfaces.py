"""
engine/kb_surfaces.py — Runtime KB table loader for source-backed gameplay constants.

Reads wiki-verified mechanic truth from KB CSV tables so that engine code
does not carry execution-authoritative literal values for gameplay data.
Engine modules must import their constants from this module, not define them inline.

Split:
  - Source-backed gameplay truth (boss constants, stat caps, workshop/lab formulas):
    loaded from KB tables here.
  - QE resolver policy (kill thresholds, resolution rules): see qe/policy.py.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

_ROOT = Path(__file__).resolve().parents[1]
_BOSS_SUMMARY_PATH = _ROOT / 'kb' / 'enemies' / 'tables' / 'wiki-verified-boss-summary.csv'
_STAT_CAPS_PATH = _ROOT / 'kb' / 'global-rules' / 'tables' / 'game-mechanic-stat-caps.csv'
_WORKSHOP_FORMULAS_PATH = _ROOT / 'kb' / 'global-rules' / 'tables' / 'workshop-formula-params-canonical.csv'


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_boss_constants() -> dict[str, float]:
    """
    Return {rule: value} for boss mechanic constants from wiki-verified-boss-summary.csv.

    Values are converted to engine internal units:
      - health_multiplier_vs_basic: raw multiplier (20.0), 'x' prefix stripped
      - *_pct rules: percentage divided by 100 to give fraction (e.g. 3.75 -> 0.0375)
    """
    rows = _read_csv(_BOSS_SUMMARY_PATH)
    result: dict[str, float] = {}
    for row in rows:
        rule = row['rule'].strip()
        raw = row['value_or_note'].strip()
        try:
            numeric = float(raw.lstrip('x'))
        except (ValueError, AttributeError):
            continue
        # pct-named rules are stored as percentages; convert to fractions for engine use
        if rule.endswith('_pct'):
            result[rule] = numeric / 100.0
        else:
            result[rule] = numeric
    return result


def load_stat_caps() -> dict[str, tuple[str, float]]:
    """
    Return {stat_id: (cap_type, cap_value)} from game-mechanic-stat-caps.csv.
    cap_type is 'max' or 'min'.
    """
    rows = _read_csv(_STAT_CAPS_PATH)
    result: dict[str, tuple[str, float]] = {}
    for row in rows:
        stat_id = row['stat_id'].strip()
        cap_type = row['cap_type'].strip()
        cap_value = float(row['cap_value'])
        result[stat_id] = (cap_type, cap_value)
    return result


def _build_formula(formula_type: str, base: float, per_level: float, floor: float) -> Callable[[float], float]:
    if formula_type == 'linear':
        return lambda level, b=base, p=per_level: b + p * level
    elif formula_type == 'linear_with_floor':
        return lambda level, b=base, p=per_level, fl=floor: max(fl, b + p * level)
    elif formula_type == 'linear_from_level_plus_one':
        return lambda level, b=base, p=per_level: b + p * (level + 1)
    else:
        raise ValueError(f'Unknown formula_type in KB table: {formula_type!r}')


def load_workshop_formulas() -> tuple[dict[str, Callable], dict[str, Callable]]:
    """
    Return (workshop_formulas, lab_formulas) where each is {stat_name: callable(level) -> float}.
    Loaded from workshop-formula-params-canonical.csv.
    Lab stat names have the ' (lab)' suffix stripped.
    """
    rows = _read_csv(_WORKSHOP_FORMULAS_PATH)
    workshop: dict[str, Callable] = {}
    lab: dict[str, Callable] = {}
    for row in rows:
        source_domain = row['source_domain'].strip()
        stat_name = row['stat_name'].strip()
        formula_type = row['formula_type'].strip()
        base = float(row['base'] or 0)
        per_level = float(row['per_level'] or 0)
        floor_raw = row['floor'].strip() if row['floor'] else ''
        floor_val = float(floor_raw) if floor_raw else 0.0
        fn = _build_formula(formula_type, base, per_level, floor_val)
        key = stat_name.removesuffix(' (lab)')
        if source_domain == 'workshop':
            workshop[key] = fn
        elif source_domain == 'lab':
            lab[key] = fn
    return workshop, lab


# ---------------------------------------------------------------------------
# Module-level constants — loaded once at import time
# ---------------------------------------------------------------------------

_BOSS_CONSTANTS = load_boss_constants()
_STAT_CAPS = load_stat_caps()
_WORKSHOP_FORMULAS, _LAB_FORMULAS = load_workshop_formulas()

# Boss mechanic constants (source: kb/enemies/tables/wiki-verified-boss-summary.csv)
BOSS_HP_MULTIPLIER: float = _BOSS_CONSTANTS['health_multiplier_vs_basic']
ELECTRON_BOSS_REMAINING_HP_PCT: float = _BOSS_CONSTANTS['electron_remaining_hp_pct']
THORNS_BOSS_EFFECTIVENESS: float = _BOSS_CONSTANTS['thorns_effectiveness_vs_boss_pct']
BOSS_HEAT_UP_DAMAGE_PER_HIT_PCT: float = _BOSS_CONSTANTS['heat_up_damage_per_hit_pct']

# Stat caps (source: kb/global-rules/tables/game-mechanic-stat-caps.csv)
# {stat_id: cap_value} — preserves the interface expected by stat_resolution_core.py
CANONICAL_PCT_CAPS: dict[str, float] = {
    stat_id: cap_value for stat_id, (cap_type, cap_value) in _STAT_CAPS.items()
}

# Workshop and lab formula callables (source: kb/global-rules/tables/workshop-formula-params-canonical.csv)
WORKSHOP_FORMULA_VALUES: dict[str, Callable] = _WORKSHOP_FORMULAS
LAB_FORMULA_VALUES: dict[str, Callable] = _LAB_FORMULAS
