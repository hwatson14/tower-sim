from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Iterable


_DEFAULT_TIER_BC_PATH = (
    Path(__file__).resolve().parents[2] / "tables" / "tier14_21_battle_conditions.csv"
)


@dataclass(frozen=True)
class TierBattleCondition:
    tier: int
    bc: str
    kind: str
    value: float | None
    unit: str | None
    notes: str


def load_tier_battle_conditions(
    path: Path | None = None,
) -> list[TierBattleCondition]:
    resolved = path or _DEFAULT_TIER_BC_PATH
    if not resolved.exists():
        raise FileNotFoundError(
            f"Tier battle condition table missing: {resolved}."
        )
    with resolved.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    _validate_columns(rows, reader.fieldnames)

    parsed: list[TierBattleCondition] = []
    for row in rows:
        parsed.append(_parse_row(row, resolved))
    if not parsed:
        raise ValueError(f"Tier battle condition table is empty: {resolved}.")
    return parsed


def tier_battle_conditions_for_tier(
    tier: int,
    path: Path | None = None,
) -> list[TierBattleCondition]:
    rows = load_tier_battle_conditions(path)
    return [row for row in rows if row.tier == tier]


def _validate_columns(rows: list[dict[str, str]], fieldnames: Iterable[str] | None) -> None:
    if fieldnames is None:
        raise ValueError("Tier battle condition table missing header row.")
    required = {"tier", "bc", "kind", "value", "unit", "notes"}
    missing = required - set(fieldnames)
    if missing:
        raise ValueError(
            "Tier battle condition table missing column(s): "
            f"{sorted(missing)}."
        )
    if rows and any(key not in required for key in rows[0].keys()):
        # csv.DictReader may include extra columns (as keys). We allow extras, but
        # if present, ensure required columns are available via fieldnames check.
        return


def _parse_row(row: dict[str, str], path: Path) -> TierBattleCondition:
    try:
        tier = int(row["tier"].strip())
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Invalid tier value in {path}: {row.get('tier')!r}") from exc
    bc = _require_field(row, "bc", path)
    kind = _require_field(row, "kind", path)
    unit = row.get("unit", "").strip() or None
    notes = row.get("notes", "").strip()
    value = _parse_value(kind, row, path)
    unit = _resolve_unit(kind, unit, row, path)
    return TierBattleCondition(
        tier=tier,
        bc=bc,
        kind=kind,
        value=value,
        unit=unit,
        notes=notes,
    )


def _require_field(row: dict[str, str], key: str, path: Path) -> str:
    if key not in row:
        raise ValueError(f"Missing {key!r} in tier battle condition row: {row} ({path})")
    value = row[key].strip()
    if value == "":
        raise ValueError(
            f"Empty {key!r} in tier battle condition row: {row} ({path})"
        )
    return value


def _parse_value(kind: str, row: dict[str, str], path: Path) -> float | None:
    raw = row.get("value", "").strip()
    if raw == "":
        if kind == "MISSING":
            return None
        raise ValueError(f"Empty 'value' in tier battle condition row: {row} ({path})")
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid value in {path}: {raw!r}") from exc


def _resolve_unit(
    kind: str, unit: str | None, row: dict[str, str], path: Path
) -> str | None:
    if unit is None:
        if kind == "MISSING":
            return None
        raise ValueError(f"Empty 'unit' in tier battle condition row: {row} ({path})")
    return unit
