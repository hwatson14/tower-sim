from __future__ import annotations

from pathlib import Path


PLAN_PATH = Path("STAT_PIPELINE_REFACTOR_PLAN.md")


def test_plan_declares_stage_membership_table() -> None:
    text = PLAN_PATH.read_text(encoding="utf-8")
    assert "## Stage membership table (authoritative for migration)" in text
    assert "| Contributor class | Stage 1 Base" in text


def test_plan_declares_orchestrator_contract() -> None:
    text = PLAN_PATH.read_text(encoding="utf-8")
    assert "## Canonical orchestrator contract (single runtime entrypoint)" in text
    assert "build_canonical_stat_pipeline(" in text


def test_plan_requires_golden_stats_fixture() -> None:
    text = PLAN_PATH.read_text(encoding="utf-8")
    assert "## 2) Golden stats fixture tests (external anchor)" in text
    assert "tower_hp" in text
    assert "eals_pct" in text
