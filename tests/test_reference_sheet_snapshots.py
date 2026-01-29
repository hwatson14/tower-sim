import csv
import sys
from pathlib import Path


def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.loaders.tier_battle_conditions import load_tier_battle_conditions  # noqa: E402


def _load_snapshot_rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


def _tier_columns(rows: list[list[str]]) -> dict[str, int]:
    for row in rows:
        if len(row) > 2 and row[2].strip() == "Battle Conditions":
            columns: dict[str, int] = {}
            for idx, value in enumerate(row):
                if idx < 3:
                    continue
                label = value.strip()
                if label:
                    columns[label] = idx
            return columns
    raise AssertionError("Battle Conditions header row not found in snapshot")


def _battle_condition_values(
    rows: list[list[str]],
    columns: dict[str, int],
    label: str,
    tiers: list[str],
) -> dict[str, float]:
    for row in rows:
        if len(row) > 2 and row[2].strip() == label:
            values: dict[str, float] = {}
            for tier in tiers:
                col = columns[tier]
                raw = row[col].strip()
                if raw == "":
                    raise AssertionError(f"Missing value for {label} tier {tier}")
                values[tier] = float(raw)
            return values
    raise AssertionError(f"Row not found for battle condition {label}")


def test_reference_sheet_tier_bc_snapshot() -> None:
    snapshot_path = Path("tests/fixtures/tower-sim-data/Tiers.csv")
    rows = _load_snapshot_rows(snapshot_path)
    columns = _tier_columns(rows)

    tier_labels = ["14", "15"]
    reference_map = {
        "PC Dmg": "plasma_cannon_resistance",
        "Thorn Dmg": "thorns_resistance",
        "Orb Dmg": "orb_resistance",
        "Death Ray Dmg": "death_ray_resistance",
    }

    catalog = load_tier_battle_conditions(
        Path("reference/step1_dump_docs/part2_data/tier14_21_battle_conditions.csv"),
        allow_incomplete=True,
    )

    for sheet_label, bc_name in reference_map.items():
        expected = _battle_condition_values(rows, columns, sheet_label, tier_labels)
        for tier_label in tier_labels:
            tier = int(tier_label)
            matches = [
                row
                for row in catalog.for_tier(tier)
                if row.name == bc_name and row.kind == "damage_multiplier"
            ]
            assert matches, f"Missing battle condition {bc_name} for tier {tier}"
            assert matches[0].value == expected[tier_label]
