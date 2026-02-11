from __future__ import annotations

from pathlib import Path

from tower_sim.audit.naming_contract_check import run_naming_contract_check


def test_naming_contract_check_passes_with_fixture_snapshot() -> None:
    result = run_naming_contract_check(
        ids_path=Path("tests/fixtures/tower-sim-data/_IDS.csv")
    )

    assert result["status"] == "ok"
    assert result["errors"] == []
    assert result["snapshot_loaded"] is True
    assert result["entity_category_sizes"]["cards"] > 0
    assert result["entity_category_sizes"]["workshop"] > 0
