from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

_DEFAULT_TABLES_DIR = Path(__file__).resolve().parents[2] / "tables"
_LEVEL_COLUMNS = tuple(f"level_{idx}" for idx in range(10))


@dataclass(frozen=True)
class CardMasteryRow:
    card_mastery: str
    stone_cost: int
    description: str
    level_values: tuple[str, ...]
    provenance: str


def load_card_mastery_rows(path: Path | None = None) -> list[CardMasteryRow]:
    csv_path = path or (_DEFAULT_TABLES_DIR / "card_masteries_v1.csv")
    required_columns = {
        "card_mastery",
        "stone_cost",
        "description",
        "provenance",
        *_LEVEL_COLUMNS,
    }
    rows = _read_csv_rows(csv_path, required_columns)
    parsed: list[CardMasteryRow] = []
    seen: set[str] = set()
    for row in rows:
        name = _require(row, "card_mastery", csv_path)
        if name in seen:
            raise ValueError(f"Duplicate card mastery {name!r} in {csv_path}")
        seen.add(name)
        stone_cost = _parse_int(row, "stone_cost", csv_path)
        description = _require(row, "description", csv_path)
        values = tuple(
            _require(row, column, csv_path) for column in _LEVEL_COLUMNS
        )
        if len(values) != len(_LEVEL_COLUMNS):
            raise ValueError(
                f"Card mastery {name!r} missing level values in {csv_path}"
            )
        provenance = _require(row, "provenance", csv_path)
        parsed.append(
            CardMasteryRow(
                card_mastery=name,
                stone_cost=stone_cost,
                description=description,
                level_values=values,
                provenance=provenance,
            )
        )
    if not parsed:
        raise ValueError(f"Card mastery table is empty: {csv_path}")
    return parsed


def load_card_mastery_map(
    path: Path | None = None,
) -> dict[str, CardMasteryRow]:
    rows = load_card_mastery_rows(path)
    return {row.card_mastery: row for row in rows}


def _read_csv_rows(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing table: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Table missing headers: {path}")
        fieldnames = [name.strip() for name in reader.fieldnames]
        if set(fieldnames) != required_columns:
            raise ValueError(
                f"Table schema mismatch for {path}. Expected {sorted(required_columns)}, "
                f"got {fieldnames}."
            )
        return list(reader)


def _require(row: Mapping[str, str], key: str, path: Path) -> str:
    value = row.get(key, "").strip()
    if value == "":
        raise ValueError(f"Missing {key!r} in {path}: {row}")
    return value


def _parse_int(row: Mapping[str, str], key: str, path: Path) -> int:
    raw = _require(row, key, path)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid {key} {raw!r} in {path}") from exc
    if not value.is_integer():
        raise ValueError(f"Non-integer {key} {raw!r} in {path}")
    return int(value)


__all__ = ["CardMasteryRow", "load_card_mastery_rows", "load_card_mastery_map"]
