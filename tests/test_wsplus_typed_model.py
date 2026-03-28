from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from input.runtime_state import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from models.account_state import WorkshopEnhancementSnapshot
from input.ids_parser import parse_ids


def test_wsplus_tracks_compile_as_typed_preset_aware_state():
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)
    assert state.workshop_enhancement_tracks
    damage = state.workshop_enhancement_tracks["Damage +"]
    assert damage.preset_levels["Farming"] is not None
    assert damage.current_multiplier is not None


def test_wsplus_stat_inputs_are_selected_by_bound_preset_lane():
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)
    synthetic = WorkshopEnhancementSnapshot(
        name="Synthetic Test +",
        current_multiplier=9.9,
        preset_levels={"Farming": 10, "Tourney": 30, "Milestone": None, "Preset 4": None, "Preset 5": None},
        max_level=99,
    )
    mutated = replace(state, workshop_enhancement_tracks={**state.workshop_enhancement_tracks, synthetic.name: synthetic})
    farming_rows = [row for row in compile_stat_inputs(mutated, preset_name="Farming", state_mode="start_of_run") if row.stat_name == synthetic.name]
    tourney_rows = [row for row in compile_stat_inputs(mutated, preset_name="Tourney", state_mode="start_of_run") if row.stat_name == synthetic.name]
    assert farming_rows and tourney_rows
    assert farming_rows[0].raw_level == 10
    assert tourney_rows[0].raw_level == 30
    assert abs(float(farming_rows[0].value) - 1.10) < 1e-9
    assert abs(float(tourney_rows[0].value) - 1.30) < 1e-9
