from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[1]
KB_PERKS_TABLES = ROOT / "kb" / "perks" / "tables"
DEFAULT_TABLE_PATHS = {
    "perks": KB_PERKS_TABLES / "perks.csv",
    "perk_pool_weights": KB_PERKS_TABLES / "perk-pool-weights.csv",
    "perk_wave_requirement_steps": KB_PERKS_TABLES / "perk-wave-requirement-steps.csv",
}


@dataclass(frozen=True)
class PerkDefinition:
    perk_name: str
    category: str
    effect: str
    max_picks: int
    stacking_type: str | None
    effect_stat_name: str | None
    effect_stat_id: str | None
    required_uw: str | None
    notes: str
    source: str


@dataclass(frozen=True)
class PerkPoolWeight:
    category: str
    weight_percent: float
    notes: str
    source: str


@dataclass(frozen=True)
class PerkWaveRequirementStep:
    perks_taken_threshold: int
    base_waves_required: int


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
    "required_uw",
    "notes",
    "source",
)

POOL_WEIGHT_COLUMNS = (
    "category",
    "weight_percent",
    "notes",
    "source",
)

WAVE_REQUIREMENT_STEP_COLUMNS = (
    "perks_taken_threshold",
    "base_waves_required",
)


def resolve_perk_table_path(table_name: str) -> Path:
    try:
        return DEFAULT_TABLE_PATHS[table_name]
    except KeyError as exc:
        supported = ", ".join(sorted(DEFAULT_TABLE_PATHS))
        raise PerkTableError(
            f"Unknown perk table {table_name!r}. Supported tables: {supported}."
        ) from exc


def load_perk_definitions(path: Path | None = None) -> List[PerkDefinition]:
    resolved = path or resolve_perk_table_path("perks")
    rows = _read_rows(resolved, REQUIRED_COLUMNS)
    perks: List[PerkDefinition] = []
    for row in rows:
        perk_name = row["perk_name"].strip()
        if not perk_name:
            raise PerkTableError(f"Missing perk_name in {resolved}.")
        stacking_type = row["stacking_type"].strip() or None
        effect_stat_name = row["effect_stat_name"].strip() or None
        effect_stat_id = row["effect_stat_id"].strip() or None
        required_uw = row["required_uw"].strip() or None
        category = row["category"].strip()
        if category == "ultimate_weapon" and not required_uw:
            raise PerkTableError(f"Ultimate-weapon perk {perk_name!r} must declare required_uw in {resolved}.")
        perks.append(
            PerkDefinition(
                perk_name=perk_name,
                category=category,
                effect=row["effect"].strip(),
                max_picks=_parse_int(row["max_picks"], resolved, perk_name),
                stacking_type=stacking_type,
                effect_stat_name=effect_stat_name,
                effect_stat_id=effect_stat_id,
                required_uw=required_uw,
                notes=row["notes"].strip(),
                source=row["source"].strip(),
            )
        )
    return perks


def load_perk_pool_weights(path: Path | None = None) -> List[PerkPoolWeight]:
    resolved = path or resolve_perk_table_path("perk_pool_weights")
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


def load_perk_wave_requirement_steps(path: Path | None = None) -> List[PerkWaveRequirementStep]:
    resolved = path or resolve_perk_table_path("perk_wave_requirement_steps")
    rows = _read_rows(resolved, WAVE_REQUIREMENT_STEP_COLUMNS)
    steps: List[PerkWaveRequirementStep] = []
    for row in rows:
        steps.append(
            PerkWaveRequirementStep(
                perks_taken_threshold=_parse_int(row["perks_taken_threshold"], resolved, "threshold"),
                base_waves_required=_parse_int(row["base_waves_required"], resolved, "base_wr"),
            )
        )
    if not steps:
        raise PerkTableError(f"Wave requirement step table is empty: {resolved}")
    steps.sort(key=lambda s: s.perks_taken_threshold, reverse=True)
    return steps


def _read_rows(path: Path, required_columns: Iterable[str]) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing perk table: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
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
    "DEFAULT_TABLE_PATHS",
    "PerkDefinition",
    "PerkPoolWeight",
    "PerkWaveRequirementStep",
    "PerkTableError",
    "load_perk_definitions",
    "load_perk_pool_weights",
    "load_perk_wave_requirement_steps",
    "resolve_perk_table_path",
]
