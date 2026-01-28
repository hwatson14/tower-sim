import sys
from pathlib import Path


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.tier_battle_conditions import load_tier_battle_conditions  # noqa: E402


def test_load_tier_battle_conditions_rejects_incomplete_rows() -> None:
    path = Path("reference/step1_dump_docs/part2_data/tier14_21_battle_conditions.csv")
    try:
        load_tier_battle_conditions(path)
    except ValueError as exc:
        assert "Invalid tier battle condition row" in str(exc)
    else:
        raise AssertionError("Expected ValueError for incomplete rows")

def test_load_tier_battle_conditions_allows_skip_incomplete() -> None:
    path = Path("reference/step1_dump_docs/part2_data/tier14_21_battle_conditions.csv")
    catalog = load_tier_battle_conditions(path, allow_incomplete=True)

    assert catalog.rows
    tier_14 = catalog.for_tier(14)
    assert any(row.name == "orb_resistance" and row.value == 0.50 for row in tier_14)
