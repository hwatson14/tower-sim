from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from engine.stat_engine import resolve_stats
from models.stat_input import StatInput


def test_locked_uw_mechanic_param_resolves_to_zero():
    rows = [
        StatInput(
            stat_name="Golden Tower::Unlocked",
            source_family="uw_unlock",
            source_name="Golden Tower",
            value=False,
            value_type="bool",
            stage="account_state",
            provenance="IDS::UWs",
            destination_object_type="capability",
            destination_id="uw.golden_tower.owned",
            resolver_id="standard_bool",
            kb_mapped=True,
        ),
        StatInput(
            stat_name="Golden Tower::Bonus",
            source_family="uw",
            source_name="Golden Tower",
            value=17.9,
            value_type="resolved_value",
            stage="account_state",
            provenance="IDS::UWs",
            destination_object_type="mechanic_param",
            destination_id="uw.golden_tower.bonus_multiplier",
            resolver_id="standard_scalar_param",
            kb_mapped=True,
        ),
    ]
    statbook = resolve_stats(rows)
    row = statbook.rows["mechanic_param::uw.golden_tower.bonus_multiplier"]
    assert row.final_value == 0.0
    assert row.status == "resolved"
    assert "not owned" in row.notes.lower()


def test_owned_uw_mechanic_param_preserves_value():
    rows = [
        StatInput(
            stat_name="Golden Tower::Unlocked",
            source_family="uw_unlock",
            source_name="Golden Tower",
            value=True,
            value_type="bool",
            stage="account_state",
            provenance="IDS::UWs",
            destination_object_type="capability",
            destination_id="uw.golden_tower.owned",
            resolver_id="standard_bool",
            kb_mapped=True,
        ),
        StatInput(
            stat_name="Golden Tower::Bonus",
            source_family="uw",
            source_name="Golden Tower",
            value=17.9,
            value_type="resolved_value",
            stage="account_state",
            provenance="IDS::UWs",
            destination_object_type="mechanic_param",
            destination_id="uw.golden_tower.bonus_multiplier",
            resolver_id="standard_scalar_param",
            kb_mapped=True,
        ),
    ]
    statbook = resolve_stats(rows)
    row = statbook.rows["mechanic_param::uw.golden_tower.bonus_multiplier"]
    assert row.final_value == 17.9
    assert row.status == "resolved"
