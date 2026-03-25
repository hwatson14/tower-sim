from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from compilers.account_state_compiler import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from parsers.ids_parser import parse_ids


def test_guardian_tracks_are_compiled_as_typed_state():
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)
    assert state.guardian_tracks, "Expected typed guardian tracks in compiled account state."
    assert "Scout" in state.guardian_tracks
    scout_track_names = {track.track_name for track in state.guardian_tracks["Scout"]}
    assert "Cooldown" in scout_track_names


def test_guardian_stat_inputs_use_typed_model_metadata():
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)
    rows = compile_stat_inputs(state, preset_name="Farming", state_mode="start_of_run")
    guardian_rows = [row for row in rows if row.source_family == "guardian" and row.source_name == "Scout" and row.stat_name.endswith("::Cooldown")]
    assert guardian_rows, "Expected Scout::Cooldown guardian stat row."
    row = guardian_rows[0]
    assert row.raw_level is not None
    assert row.resolved_value is not None
