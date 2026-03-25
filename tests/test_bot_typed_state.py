from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from compilers.account_state_compiler import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from parsers.ids_parser import parse_ids


def test_bot_compiled_state_preserves_level_and_resolved_value_metadata():
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)

    golden_tracks = state.bot_upgrade_tracks.get("Golden Bot", [])
    assert golden_tracks, "Expected typed bot tracks for Golden Bot."
    bonus_track = next(track for track in golden_tracks if track.track_name == "Bonus")
    assert bonus_track.level == 22
    assert abs(bonus_track.resolved_value - 6.4) < 1e-6
    assert bonus_track.resolved_unit == "x"


def test_bot_stat_inputs_expose_level_resolved_value_and_unit():
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)
    rows = compile_stat_inputs(state, preset_name="Farming", state_mode="start_of_run")
    bot_rows = [row for row in rows if row.source_family == "bot" and row.source_name == "Golden Bot" and row.stat_name.endswith("::Bonus")]
    assert bot_rows, "Expected Golden Bot::Bonus row."
    row = bot_rows[0]
    assert row.raw_level == 22
    assert abs(row.resolved_value - 6.4) < 1e-6
    assert row.resolved_unit == "x"
