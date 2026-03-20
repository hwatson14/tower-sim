from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_golden_tower_bonus_lab_routes_as_additive_mechanic_param():
    statbook = json.loads((ROOT / "out" / "statbook.json").read_text())["rows"]
    row = statbook["mechanic_param::uw.golden_tower.bonus_multiplier"]
    contributors = row["contributors"]
    names = {(c.get("source_family"), c.get("source_name")) for c in contributors}
    assert ("uw", "Golden Tower") in names
    assert ("lab", "Golden Tower Bonus") in names
    contrib = next(c for c in contributors if c.get("source_family") == "lab" and c.get("source_name") == "Golden Tower Bonus")
    assert abs(float(contrib["value"]) - 3.3) < 1e-9


def test_chrono_field_reduction_pct_routes_as_bonus_above_unlock_base():
    statbook = json.loads((ROOT / "out" / "statbook.json").read_text())["rows"]
    row = statbook["mechanic_param::uw.chrono_field.damage_reduction_pct"]
    contributors = row["contributors"]
    base = next(c for c in contributors if c.get("source_name") == "Chrono Field Damage Reduction")
    bonus = next(c for c in contributors if c.get("source_name") == "Chrono Field Reduction %")
    assert abs(float(base["value"]) - 10.0) < 1e-9
    assert abs(float(bonus["value"]) - 10.0) < 1e-9
    assert abs(float(row["final_value"]) - 20.0) < 1e-9
