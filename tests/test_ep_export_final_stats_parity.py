from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.audit.ep_export_final_stats_parity import verify_final_stats_against_ep_export
from tower_sim.engines.combat_stat_derivation import build_canonical_stat_inputs
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.spec_loader import load_problem_spec
from tower_sim.registry.stat_registry import Phase, default_registry


def _ids_path() -> Path:
    return Path("tests/fixtures/tower-sim-data/_IDS.csv")


def _spec_path(name: str) -> Path:
    return Path("tests/fixtures/specs") / name


def test_verify_final_stats_enforces_preset_mapping() -> None:
    with pytest.raises(ValueError, match="Preset mismatch"):
        verify_final_stats_against_ep_export(
            ids_path=_ids_path(),
            spec_path=_spec_path("tournament_champion_spec.yaml"),
            suite="ehp",
        )


def test_verify_final_stats_returns_comparison_report() -> None:
    report = verify_final_stats_against_ep_export(
        ids_path=_ids_path(),
        spec_path=_spec_path("real_build_pipeline_spec.yaml"),
        suite="ehp",
    )

    assert report["preset"] == "farming"
    assert report["spec_mode"] == "farming"
    assert report["matched_count"] + report["mismatch_count"] == len(report["compared_rows"])
    assert len(report["compared_rows"]) > 0
    assert {entry["key"] for entry in report["decisive_lineage"]} == {
        "health",
        "health_regen",
        "defense_percent",
        "wall_health",
        "wall_regen",
    }


def test_verify_final_stats_real_build_mode_exposes_contributor_trace() -> None:
    report = verify_final_stats_against_ep_export(
        ids_path=_ids_path(),
        spec_path=_spec_path("real_build_pipeline_spec.yaml"),
        suite="ehp",
        compiled_core_only=True,
    )

    assert report["compiled_core_only"] is True
    assert set(report["contributor_trace"]) == {
        "health",
        "health_regen",
        "defense_percent",
        "wall_health",
        "wall_regen",
    }


def test_verify_final_stats_real_build_mode_surfaces_decisive_mismatches() -> None:
    report = verify_final_stats_against_ep_export(
        ids_path=_ids_path(),
        spec_path=_spec_path("real_build_pipeline_spec.yaml"),
        suite="ehp",
    )

    assert report["status"] == "mismatch"
    compared = {row["key"]: row for row in report["compared_rows"]}
    decisive = {
        "health",
        "health_regen",
        "defense_percent",
        "wall_health",
        "wall_regen",
    }
    assert decisive.issubset(compared)
    assert all(compared[key]["within_tolerance"] is False for key in decisive)


def test_real_build_parity_trace_shows_no_perk_contributor_for_decisive_stats() -> None:
    report = verify_final_stats_against_ep_export(
        ids_path=_ids_path(),
        spec_path=_spec_path("real_build_pipeline_spec.yaml"),
        suite="ehp",
    )

    assert report["status"] == "mismatch"
    assert "perk" not in report["contributor_trace"]["health"]
    assert "perk" not in report["contributor_trace"]["health_regen"]
    assert "perk" not in report["contributor_trace"]["defense_percent"]


def test_real_build_canonical_inputs_missing_wall_regen_ratio_prereq() -> None:
    ids_snapshot = compile_account_snapshot(parse_ids(_ids_path()))
    spec = load_problem_spec(_spec_path("real_build_pipeline_spec.yaml"))
    canonical = build_canonical_stat_inputs(
        problem_spec=spec,
        ids_snapshot=ids_snapshot,
        registry=default_registry(),
    )

    start_inputs = {
        item.stat_id
        for item in canonical.stat_inputs
        if item.phase == Phase.START_OF_RUN
    }

    assert "workshop_wall_health" in start_inputs
    assert "workshop_wall_regen" not in start_inputs
