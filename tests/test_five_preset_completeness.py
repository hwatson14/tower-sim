from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from input.parsers import parse_ids
from input.runtime_state import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from run_stats import (
    CANONICAL_PRESET_NAMES,
    _build_artifact_contract_manifest,
    _build_family_completeness_matrix,
)


def test_five_preset_completeness_gate():
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)
    stat_inputs = compile_stat_inputs(state, preset_name="Farming", state_mode="max_progression", perks_enabled=False)
    family_matrix = _build_family_completeness_matrix(state, stat_inputs)
    artifact_manifest = _build_artifact_contract_manifest(state, "Farming", stat_inputs, {"rows": {}})

    assert family_matrix["canonical_presets"] == list(CANONICAL_PRESET_NAMES)
    assert artifact_manifest["canonical_presets"] == list(CANONICAL_PRESET_NAMES)
    assert family_matrix["synthetic_preset_names_present"] == []
    assert artifact_manifest["synthetic_preset_names_present"] == []

    lane_sets = family_matrix["preset_lane_completeness"]
    assert set(lane_sets.keys()) == set(CANONICAL_PRESET_NAMES)
