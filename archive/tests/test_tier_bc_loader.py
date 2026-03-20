import sys
from pathlib import Path


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.loaders.tier_bc_loader import (  # noqa: E402
    load_tier_battle_conditions,
    tier_battle_conditions_for_tier,
)


def test_loads_tier_bc_table() -> None:
    rows = load_tier_battle_conditions()
    assert len(rows) == 117

    sample = next(row for row in rows if row.tier == 14 and row.bc == "orb_resistance")
    assert sample.kind == "damage_multiplier"
    assert sample.unit == "mult"
    assert sample.value == 0.5


def test_filters_by_tier() -> None:
    tier_rows = tier_battle_conditions_for_tier(21)
    assert tier_rows
    assert all(row.tier == 21 for row in tier_rows)
    skip_row = next(
        row for row in tier_rows if row.bc == "enemy_level_skip_reduction"
    )
    assert skip_row.kind == "absolute_chance_subtract"
    assert skip_row.unit == "pp"
