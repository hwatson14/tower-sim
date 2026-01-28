from __future__ import annotations

import sys
from pathlib import Path


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.stat_engine import StatEngine, StatInput  # noqa: E402
from tower_sim.stat_registry import Phase, default_registry  # noqa: E402


def test_statbook_reference_structure(tmp_path: Path) -> None:
    registry = default_registry()
    engine = StatEngine(registry=registry)
    inputs = [
        StatInput(
            stat_id="tower_hp",
            phase=Phase.START_OF_RUN,
            base_value=100,
            loadout_delta=20,
            enhancement_multiplier=1.1,
            tier_rule_delta=5,
            provenance="test/base",
        ),
        StatInput(
            stat_id="tower_hp",
            phase=Phase.END_OF_RUN,
            base_value=120,
            loadout_delta=30,
            enhancement_multiplier=1.05,
            tier_rule_multiplier=0.9,
            provenance="test/end",
        ),
    ]
    result = engine.build(inputs)
    csv_path = tmp_path / "statbook.csv"
    result.statbook.to_csv(csv_path)

    content = csv_path.read_text(encoding="utf-8")
    assert "stat_id" in content
    assert "tier_rule_delta_or_multiplier" in content
    assert "tower_hp" in content
    phases = {row.phase for row in result.statbook.rows}
    assert {Phase.START_OF_RUN.value, Phase.END_OF_RUN.value}.issubset(phases)
