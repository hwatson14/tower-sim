from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from parsers.ids_parser import parse_ids
from compilers.account_state_compiler import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from engine.stat_engine import resolve_stats
from engine.query_surface_publication import publish_phase3_query_surfaces
from run_stats import (
    CANONICAL_PRESET_NAMES,
    _build_artifact_contract_manifest,
    _build_family_completeness_matrix,
)


def _build_state():
    ids = parse_ids(ROOT / "input" / "_IDS.csv")
    state = compile_account_state(ids)
    stat_inputs = compile_stat_inputs(state, preset_name="Farming", state_mode="max_progression", perks_enabled=False)
    statbook = resolve_stats(stat_inputs)
    publish_phase3_query_surfaces(statbook.rows)
    return state, stat_inputs, statbook.to_dict()


def test_artifact_contract_manifest_declares_explicit_class_and_provenance():
    state, stat_inputs, statbook = _build_state()
    manifest = _build_artifact_contract_manifest(state, "Farming", stat_inputs, statbook)
    contracts = {entry["surface"]: entry for entry in manifest["artifacts"]}
    assert contracts["account_state.json"]["artifact_class"] == "canonical_snapshot"
    assert contracts["account_state.json"]["contract"] == "full"
    assert contracts["account_state.json"]["provenance"] == "current_run_generated"
    assert contracts["statbook_publishable.json"]["artifact_class"] == "publishable_view"
    assert contracts["statbook_publishable.json"]["contract"] == "partial"
    assert contracts["ep_oracle_compare.json"]["artifact_class"] == "compare_view"
    assert contracts["family_completeness_matrix.json"]["artifact_class"] == "audit_manifest"


def test_artifact_contract_manifest_uses_canonical_five_preset_contract():
    state, stat_inputs, statbook = _build_state()
    manifest = _build_artifact_contract_manifest(state, "Farming", stat_inputs, statbook)
    assert manifest["canonical_presets"] == list(CANONICAL_PRESET_NAMES)
    assert manifest["canonical_preset_count"] == 5
    assert manifest["synthetic_preset_names_present"] == []
