from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from input.parsers import parse_ids
from input.runtime_state import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from run_stats import CANONICAL_PRESET_NAMES, _build_family_completeness_matrix


def test_family_completeness_matrix_exposes_five_preset_lane_state():
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)
    stat_inputs = compile_stat_inputs(state, preset_name="Farming", state_mode="max_progression", perks_enabled=False)
    matrix = _build_family_completeness_matrix(state, stat_inputs)
    assert matrix["canonical_presets"] == list(CANONICAL_PRESET_NAMES)
    for preset in CANONICAL_PRESET_NAMES:
        assert preset in matrix["preset_lane_completeness"]
        lane = matrix["preset_lane_completeness"][preset]
        assert "cards_explicit" in lane
        assert "modules_explicit" in lane
        assert "perks_explicit" in lane


def test_family_completeness_matrix_has_family_mapping_counts():
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)
    stat_inputs = compile_stat_inputs(state, preset_name="Farming", state_mode="max_progression", perks_enabled=False)
    matrix = _build_family_completeness_matrix(state, stat_inputs)
    families = matrix["families"]
    assert "workshop" in families
    assert "lab" in families
    assert "card" in families
    assert "module" in families
    for family, payload in families.items():
        assert payload["total_rows"] >= payload["mapped_rows"]
        assert payload["total_rows"] >= payload["unmapped_rows"]
        assert payload["mapped_rows"] + payload["unmapped_rows"] == payload["total_rows"]
