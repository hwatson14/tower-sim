from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

from input.state_types import ScenarioRuntimeInputs, projection_state_for_mode
from simulators.scenario import ScenarioConfig, ScenarioSurfaces
from simulators.timing import TimingSurfaces, resolve_combat_runtime_surfaces

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


def test_mapping_with_canonical_namespaced_keys__values_are_loaded():
    inputs = ScenarioRuntimeInputs.from_mapping(
        {
            "state::combat.orb_boss_hit_pct": 2.5,
            "state::combat.effective_damage_reduction_pct": 98.0,
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
        "orb_boss_total_damage_pct",
        "orb_boss_hit_count",
        "electron_total_damage_pct",
        "electron_hit_count",
        "orb_boss_hits_per_second",
        "electron_hits_per_second",
        "boss_time_to_contact_seconds",
        "boss_hit_interval_seconds",
        "effective_damage_reduction_pct",
        "incoming_damage_multiplier",
        "flame_bot_damage_reduction_pct",
        "flame_bot_duration_seconds",
        "flame_bot_cooldown_seconds",
        "defense_field_damage_reduction_pct",
        "defense_field_duration_seconds",
        "defense_field_cooldown_seconds",
        "black_hole_damage_reduction_pct",
        "black_hole_duration_seconds",
        "black_hole_cooldown_seconds",
        "pbh_encounter_uptime_fraction",
        "death_wave_health_max_multiplier",
        "death_wave_health_max_wave",
        "boss_wave_interval",
        "enemy_level_skip_reduction_pp",
    }
    assert fields == expected


def test_total_boss_hit_counts_are_consumed_for_replacement_boss_waves():
    runtime_inputs = ScenarioRuntimeInputs.from_mapping(
        {
            "orb_boss_hits_total": 4,
            "state::combat.electron_hit_count": 6,
        }
    )

    assert runtime_inputs.orb_boss_hit_count == pytest.approx(4.0)
    assert runtime_inputs.electron_hit_count == pytest.approx(6.0)


def test_total_boss_damage_fields_are_consumed_for_replacement_boss_waves():
    runtime_inputs = ScenarioRuntimeInputs.from_mapping(
        {
            "orb_boss_damage_total_pct": 50,
            "state::combat.electron_total_damage_pct": 25,
        }
    )

    assert runtime_inputs.orb_boss_total_damage_pct == pytest.approx(50.0)
    assert runtime_inputs.electron_total_damage_pct == pytest.approx(25.0)


def test_non_positive_rate_field__raises_value_error():
    with pytest.raises(ValueError, match="> 0.0"):
        ScenarioRuntimeInputs.from_mapping({"electron_hits_per_second": 0.0})


def test_electron_hits_per_second_is_consumed_from_scenario_runtime_input_owner_seam():
    runtime_inputs = ScenarioRuntimeInputs.from_mapping({"electron_hits_per_second": 5.0})
    resolved = resolve_combat_runtime_surfaces(
        config=ScenarioConfig(mode_id="farming", tier=1),
        scenario=ScenarioSurfaces(),
        timing=TimingSurfaces(),
        scenario_runtime_inputs=runtime_inputs,
    )

    assert resolved.electron_hits_per_second == pytest.approx(5.0)
    assert any("scenario runtime input owner seam" in note for note in resolved.source_notes)


def test_projection_state_for_mode__max_progression_sets_expected_facets():
    projection = projection_state_for_mode("max_progression")
    assert projection.max_workshop is True
    assert projection.projected_perks is True
    assert projection.death_wave_health is True
    assert projection.berserker_damage_bonus is True

