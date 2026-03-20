from __future__ import annotations

from tower_sim.audit.stat_source_coverage import CoverageStatus, audit_stat_coverage
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.libs import labs_lib, workshop_lib
from tower_sim.registry.stat_registry import default_registry


def test_stat_source_coverage_lab_presence() -> None:
    ids_raw = parse_ids()
    snapshot = compile_account_snapshot(ids_raw)
    report = audit_stat_coverage(
        ids=snapshot,
        workshop_lib=workshop_lib,
        labs_lib=labs_lib,
        registry=default_registry(),
    )

    assert any(item.status == CoverageStatus.COVERED for item in report.labs)
    assert any(
        item.status in {CoverageStatus.MISSING_TABLE, CoverageStatus.NOT_PROMOTABLE}
        for item in report.labs
    )
