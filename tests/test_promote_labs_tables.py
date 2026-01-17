from __future__ import annotations

import csv
from pathlib import Path

from tower_sim.wiki.promote_labs_tables import build_labs_values_v1


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def test_promote_labs_tables_builds_expected_csv(tmp_path: Path) -> None:
    output_path = tmp_path / "labs_values_v1.csv"

    build_labs_values_v1(output_path)

    assert output_path.exists()
    rows = _load_rows(output_path)
    assert len(rows) == 340

    expected_counts = {
        "LAB_ENEMY_ATTACK_LEVEL_SKIP": 20,
        "LAB_ENEMY_HEALTH_LEVEL_SKIP": 20,
        "LAB_HEALTH": 100,
        "LAB_HEALTH_REGEN": 100,
        "LAB_RECOVERY_PACKAGE_CHANCE": 20,
        "LAB_WALL_HEALTH": 50,
        "LAB_WALL_REGEN": 30,
    }
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["lab_canonical_id"]] = counts.get(row["lab_canonical_id"], 0) + 1
    assert counts == expected_counts

    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["lab_canonical_id"], row["level"])
        assert key not in seen
        seen.add(key)

        float(row["value"])
        assert row["unit"] in {"percent_points", "percent", "raw_number"}
