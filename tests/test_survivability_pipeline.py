from __future__ import annotations

from pathlib import Path

import pytest

from tower_sim.engines.survivability_pipeline import (
    _parse_module_blocks,
    build_survivability_report,
)
from tower_sim.loaders.account_snapshot_compiler import (
    compile_account_snapshot,
    resolve_loadout,
)
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.spec_loader import load_problem_spec


def test_survivability_pipeline_snapshots() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.json"))

    report = build_survivability_report(
        ids_snapshot, spec, module_context="Testing", allow_provisional=True
    )

    snapshots = report["snapshots"]
    assert "base_only" in snapshots
    assert "start_of_run" in snapshots
    assert "at_wave" in snapshots
    assert "wave_state" in snapshots["at_wave"]
    assert "orb_damage_mult" in snapshots["at_wave"]["applied_bc"]

    verdict = report["survivability_verdict"]
    assert isinstance(verdict["ttk_seconds"], float)
    assert isinstance(verdict["ttd_seconds"], float)


def test_module_override_changes_armor_effects() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.json"))
    resolved = resolve_loadout(ids_snapshot, "Testing")
    armor_block = _parse_module_blocks(ids_snapshot, resolved)["Armor"]
    modules = list(armor_block.inventory.values())
    primary = modules[0]
    alternate = next(
        module for module in modules if module.main_effect != primary.main_effect
    )

    base_report = build_survivability_report(
        ids_snapshot,
        spec,
        module_context="Testing",
        module_overrides={"Armor": {"primary": primary.name}},
        allow_provisional=True,
    )
    alt_report = build_survivability_report(
        ids_snapshot,
        spec,
        module_context="Testing",
        module_overrides={"Armor": {"primary": alternate.name}},
        allow_provisional=True,
    )
    assert (
        base_report["snapshots"]["start_of_run"]["tower_hp"]
        != alt_report["snapshots"]["start_of_run"]["tower_hp"]
    )


def test_base_only_matches_effective_paths_fixture() -> None:
    ids_snapshot = compile_account_snapshot(
        parse_ids(Path("tests/fixtures/tower-sim-data/_IDS.csv"))
    )
    spec = load_problem_spec(Path("tests/fixtures/specs/sample_spec.json"))

    report = build_survivability_report(
        ids_snapshot, spec, module_context="Testing", allow_provisional=True
    )
    base_only = report["snapshots"]["base_only"]
    assert base_only["tower_hp"] == pytest.approx(11314998536.23848, rel=1e-9)
    assert base_only["tower_regen"] == pytest.approx(30919400339.730965, rel=1e-9)
    assert base_only["def_pct"] == pytest.approx(0.551, rel=1e-9)
    assert base_only["wall_hp"] == pytest.approx(28740096282.04574, rel=1e-9)
    assert base_only["wall_regen"] == pytest.approx(64930740713.43503, rel=1e-9)
