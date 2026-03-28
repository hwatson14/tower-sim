from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

from input.state_types import ScenarioRuntimeInputs, projection_state_for_mode

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


def test_mapping_with_namespaced_keys__values_are_loaded():
    inputs = ScenarioRuntimeInputs.from_mapping(
        {
            "runtime_mechanic_param::combat.orb_boss_hit_pct": 2.5,
            "runtime_mechanic_param::combat.effective_damage_reduction_pct": 98.0,
        }
    )
    assert inputs.orb_boss_hit_pct == 2.5
    assert inputs.effective_damage_reduction_pct == 98.0


def test_out_of_range_reduction__raises_value_error():
    with pytest.raises(ValueError, match="<= 100.0"):
        ScenarioRuntimeInputs.from_mapping({"effective_damage_reduction_pct": 120.0})


def test_contract_field_set__matches_expected_dataclass_fields():
    contract = yaml.safe_load(
        (ROOT / "kb" / "global-rules" / "contracts" / "scenario-runtime-inputs.yaml").read_text()
    )
    fields = set((contract or {}).get("fields", {}).keys())
    expected = {
        "orb_boss_hit_pct",
        "orb_boss_hits_per_second",
        "electron_hits_per_second",
        "boss_contact_time_seconds",
        "boss_hit_interval_seconds",
        "effective_damage_reduction_pct",
        "incoming_damage_multiplier",
        "boss_wave_interval",
        "enemy_level_skip_reduction_pp",
    }
    assert fields == expected


def test_non_positive_rate_field__raises_value_error():
    with pytest.raises(ValueError, match="> 0.0"):
        ScenarioRuntimeInputs.from_mapping({"electron_hits_per_second": 0.0})


def test_projection_state_for_mode__max_progression_sets_expected_facets():
    projection = projection_state_for_mode("max_progression")
    assert projection.max_workshop is True
    assert projection.projected_perks is True
    assert projection.death_wave_health is True
    assert projection.berserker_damage_bonus is True
