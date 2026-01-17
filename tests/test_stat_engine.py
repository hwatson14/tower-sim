from __future__ import annotations

from decimal import Decimal
import sys
from pathlib import Path

import pytest

def _add_repo_root_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))


_add_repo_root_to_path()

from tower_sim.ids_parser import parse_ids, resolve_ids_path  # noqa: E402
from tower_sim.libs import labs_lib, workshop_lib  # noqa: E402
from tower_sim.stat_engine import (  # noqa: E402
    MissingStatDataError,
    build_stat_engine,
)
from tower_sim.wiki.enemy_level_skip import workshop_level_to_chance  # noqa: E402


def _to_decimal(value: str) -> Decimal:
    return Decimal(value.replace(",", "").strip())


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1.0000000000"))


def test_stat_engine_computes_base_stats() -> None:
    ids = parse_ids(resolve_ids_path())
    tables = workshop_lib.load_workshop_tables()
    labs = labs_lib.load_labs_values()

    result = build_stat_engine(ids, workshop_tables=tables, labs_table=labs)

    def expected_workshop(
        key: str,
        workshop_level: int,
        lab_name: str,
        lab_level: int,
        unit: str,
    ) -> Decimal:
        base = _to_decimal(workshop_lib.workshop_value(key, workshop_level, tables))
        lab_value = Decimal(str(labs[lab_name].levels[lab_level]))
        if unit == "raw_number":
            return _quantize(base * lab_value)
        return _quantize(base * (Decimal("1") + lab_value / Decimal("100")))

    def expected_level_skip(entry_level: int, lab_name: str, lab_level: int) -> Decimal:
        base = Decimal(str(workshop_level_to_chance(entry_level)))
        lab_value = Decimal(str(labs[lab_name].levels[lab_level])) / Decimal("100")
        return _quantize(base + lab_value)

    start_health_level = int(float(ids.workshop.entries["Health"].coin_level))
    end_health_level = int(float(ids.workshop.entries["Health"].max_level))
    start_regen_level = int(float(ids.workshop.entries["Health Regen"].coin_level))
    end_regen_level = int(float(ids.workshop.entries["Health Regen"].max_level))

    start_eals_level = int(float(ids.workshop.entries["Enemy Attack Level Skip"].coin_level))
    end_eals_level = int(float(ids.workshop.entries["Enemy Attack Level Skip"].max_level))
    start_ehls_level = int(float(ids.workshop.entries["Enemy Health Level Skip"].coin_level))
    end_ehls_level = int(float(ids.workshop.entries["Enemy Health Level Skip"].max_level))

    lab_health_level = int(float(ids.labs.labs["Health"]))
    lab_regen_level = int(float(ids.labs.labs["Health Regen"]))
    lab_eals_level = int(float(ids.labs.labs["Enemy Attack Level Skip"]))
    lab_ehls_level = int(float(ids.labs.labs["Enemy Health Level Skip"]))

    start_tower_hp = expected_workshop(
        "Health", start_health_level, "Health", lab_health_level, "raw_number"
    )
    end_tower_hp = expected_workshop(
        "Health", end_health_level, "Health", lab_health_level, "raw_number"
    )
    start_tower_regen = expected_workshop(
        "HPregen", start_regen_level, "Health Regen", lab_regen_level, "raw_number"
    )
    end_tower_regen = expected_workshop(
        "HPregen", end_regen_level, "Health Regen", lab_regen_level, "raw_number"
    )

    start_wall_regen_lab = Decimal(
        str(labs["Wall Regen"].levels[int(float(ids.labs.labs["Wall Regen"]))])
    )
    end_wall_regen_lab = start_wall_regen_lab
    start_wall_regen = _quantize(start_tower_regen * (start_wall_regen_lab / Decimal("100")))
    end_wall_regen = _quantize(end_tower_regen * (end_wall_regen_lab / Decimal("100")))

    start_eals = expected_level_skip(
        start_eals_level, "Enemy Attack Level Skip", lab_eals_level
    )
    end_eals = expected_level_skip(
        end_eals_level, "Enemy Attack Level Skip", lab_eals_level
    )
    start_ehls = expected_level_skip(
        start_ehls_level, "Enemy Health Level Skip", lab_ehls_level
    )
    end_ehls = expected_level_skip(
        end_ehls_level, "Enemy Health Level Skip", lab_ehls_level
    )

    assert result.run_stats.start.stats["tower_hp"] == start_tower_hp
    assert result.run_stats.end.stats["tower_hp"] == end_tower_hp
    assert result.run_stats.start.stats["tower_regen"] == start_tower_regen
    assert result.run_stats.end.stats["tower_regen"] == end_tower_regen
    assert result.run_stats.start.stats["wall_regen"] == start_wall_regen
    assert result.run_stats.end.stats["wall_regen"] == end_wall_regen
    assert result.run_stats.start.stats["eals_pct"] == start_eals
    assert result.run_stats.end.stats["eals_pct"] == end_eals
    assert result.run_stats.start.stats["ehls_pct"] == start_ehls
    assert result.run_stats.end.stats["ehls_pct"] == end_ehls

    assert len(result.statbook.rows) == len(result.run_stats.start.stats) * 2
    for row in result.statbook.rows:
        assert row.base_value == row.final_value


def test_stat_engine_rejects_unknown_stat() -> None:
    ids = parse_ids(resolve_ids_path())
    with pytest.raises(MissingStatDataError, match="Unsupported stat IDs"):
        build_stat_engine(ids, include_stat_ids=["unknown_stat"])
