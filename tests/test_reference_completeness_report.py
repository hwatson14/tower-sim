from __future__ import annotations

import pytest

from tower_sim.audit import reference_completeness


pytest.importorskip("yaml")


def test_reference_completeness_report_statuses() -> None:
    report = reference_completeness.build_report()
    assert report["wave_damage"].status == "runtime"
    assert report["tournament_boss_freq"].status == "runtime"
    assert report["dag_inputs"].status == "missing"
    assert report["bc_heat"].status in {"missing", "step1-only", "runtime"}


def test_heat_wave_scalar_classification() -> None:
    report = reference_completeness.build_report()
    bc_heat = report["bc_heat"]
    missing = set(bc_heat.missing_paths)
    step1_only = set(bc_heat.step1_only_paths)
    if any(path.endswith("heat_wave_scalar.csv") for path in step1_only):
        assert "heat_wave_scalar.csv" not in missing
    else:
        assert "heat_wave_scalar.csv" in missing
