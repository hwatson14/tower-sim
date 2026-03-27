from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from input.runtime_state import compile_account_state
from input.parsers import parse_ids
from run_stats import _build_audit_surface_manifest


def test_audit_surface_manifest_labels_partial_surfaces():
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)
    manifest = _build_audit_surface_manifest(state, "Farming")
    contracts = {entry["surface"]: entry for entry in manifest["surface_contracts"]}
    assert contracts["diagnostics.json"]["contract"] == "partial"
    assert contracts["statbook_publishable.json"]["contract"] == "partial"
    assert contracts["ep_oracle_compare.json"]["contract"] == "partial"


def test_audit_surface_manifest_includes_full_completeness_and_explicit_empty_flags():
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    state = compile_account_state(ids)
    manifest = _build_audit_surface_manifest(state, "Farming")
    contracts = {entry["surface"]: entry for entry in manifest["surface_contracts"]}
    assert contracts["account_state.json"]["contract"] == "full"
    assert contracts["state_matrix.json"]["contract"] == "full"
    for preset in ("Tourney", "Farming", "Milestone", "Preset 4", "Preset 5"):
        assert preset in manifest["preset_lane_completeness"]
        lane = manifest["preset_lane_completeness"][preset]
        assert "cards_empty" in lane
        assert "modules_empty" in lane
        assert "perks_empty" in lane
