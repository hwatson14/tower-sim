from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from input.runtime_state import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from input.parsers import parse_ids


def test_uw_tracks_preserve_explicit_attribute_identity_from_ids():
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)

    assert state.uw_tracks, "Expected explicit UW tracks to be compiled."
    assert "Golden Tower" in state.uw_tracks
    track_names = [track.track_name for track in state.uw_tracks["Golden Tower"]]
    assert track_names == ["Multiplier", "Duration", "Cooldown"]


def test_uw_compiled_rows_do_not_depend_on_positional_track_names():
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)
    rows = compile_stat_inputs(state, preset_name="Farming", state_mode="start_of_run")
    uw_rows = [row for row in rows if row.source_family == "uw" and row.source_name == "Golden Tower"]
    uw_stat_names = {row.stat_name for row in uw_rows}
    assert "Golden Tower::Multiplier" in uw_stat_names
    assert "Golden Tower::Duration" in uw_stat_names
    assert "Golden Tower::Cooldown" in uw_stat_names
    assert not any("track_" in name for name in uw_stat_names)
