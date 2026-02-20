from __future__ import annotations

from pathlib import Path


PLAN_PATH = Path("STAT_PIPELINE_REFACTOR_PLAN.md")
CONTRACT_PATH = Path("CONTRACT.md")


def test_pipeline_refactor_plan_is_retired() -> None:
    assert not PLAN_PATH.exists()


def test_contract_records_migration_plan_retirement_policy() -> None:
    text = CONTRACT_PATH.read_text(encoding="utf-8")
    assert "pipeline migration plan has been retired" in text
    assert "temporary migration plans override draft diagrams while active" in text
