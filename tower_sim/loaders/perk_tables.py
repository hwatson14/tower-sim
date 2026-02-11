from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path
from typing import Dict, Iterable, List

from tower_sim.loaders.table_paths import resolve_table_path


@dataclass(frozen=True)
class PerkDefinition:
    perk_name: str
    category: str
    effect: str
    max_picks: int
    stacking_type: str | None
    effect_stat_name: str | None
    effect_stat_id: str | None
    notes: str
    source: str


@dataclass(frozen=True)
class PerkPoolWeight:
    category: str
    weight_percent: float
    notes: str
    source: str


class PerkTableError(ValueError):
    pass


REQUIRED_COLUMNS = (
    "perk_name",
    "category",
    "effect",
    "max_picks",
    "stacking_type",
    "effect_stat_name",
    "effect_stat_id",
    "notes",
    "source",
)


POOL_WEIGHT_COLUMNS = (
    "category",
    "weight_percent",
    "notes",
    "source",
)


def load_perk_definitions(path: Path | None = None) -> List[PerkDefinition]:
    resolved = path or resolve_table_path("perks")
    rows = _read_rows(resolved, REQUIRED_COLUMNS)
    perks: List[PerkDefinition] = []
    for row in rows:
        perk_name = row["perk_name"].strip()
        if not perk_name:
            raise PerkTableError(f"Missing perk_name in {resolved}.")
        stacking_type = row["stacking_type"].strip() or None
        effect_stat_name = row["effect_stat_name"].strip() or None
        effect_stat_id = row["effect_stat_id"].strip() or None
        perks.append(
            PerkDefinition(
                perk_name=perk_name,
                category=row["category"].strip(),
                effect=row["effect"].strip(),
                max_picks=_parse_int(row["max_picks"], resolved, perk_name),
                stacking_type=stacking_type,
                effect_stat_name=effect_stat_name,
                effect_stat_id=effect_stat_id,
                notes=row["notes"].strip(),
                source=row["source"].strip(),
            )
        )
    return perks


def load_perk_pool_weights(path: Path | None = None) -> List[PerkPoolWeight]:
    resolved = path or resolve_table_path("perk_pool_weights")
    rows = _read_rows(resolved, POOL_WEIGHT_COLUMNS)
    weights: List[PerkPoolWeight] = []
    for row in rows:
        category = row["category"].strip()
        if not category:
            raise PerkTableError(f"Missing category in {resolved}.")
        weights.append(
            PerkPoolWeight(
                category=category,
                weight_percent=_parse_float(row["weight_percent"], resolved, category),
                notes=row["notes"].strip(),
                source=row["source"].strip(),
            )
        )
    total_weight = sum(weight.weight_percent for weight in weights)
    if total_weight != 100.0:
        raise PerkTableError(
            f"Perk pool weight table must sum to 100.0; got {total_weight} in {resolved}."
        )
    return weights


def _read_rows(path: Path, required_columns: Iterable[str]) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing perk table: {path}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise PerkTableError(f"Missing header in {path}.")
        missing = [col for col in required_columns if col not in reader.fieldnames]
        if missing:
            raise PerkTableError(f"Perk table missing columns {missing} in {path}.")
        rows = [
            {key: (value or "") for key, value in row.items()}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    if not rows:
        raise PerkTableError(f"Perk table is empty: {path}")
    return rows


def _parse_int(raw: str, path: Path, perk_name: str) -> int:
    try:
        return int(raw)
    except ValueError as exc:
        raise PerkTableError(
            f"Invalid integer value {raw!r} for perk {perk_name} in {path}."
        ) from exc


def _parse_float(raw: str, path: Path, category: str) -> float:
    try:
        return float(raw)
    except ValueError as exc:
        raise PerkTableError(
            f"Invalid float value {raw!r} for category {category} in {path}."
        ) from exc


__all__ = [
    "PerkDefinition",
    "PerkPoolWeight",
    "PerkTableError",
    "load_perk_definitions",
    "load_perk_pool_weights",
]
