from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Dict, Iterable, List


class HeatDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class HeatWaveScalar:
    league: str
    wave: int
    scalar: float


@dataclass(frozen=True)
class BCWaveMagnitude:
    bc_id: str
    league: str
    wave: int
    magnitude: float


@dataclass(frozen=True)
class HeatBundle:
    heat_scalars: List[HeatWaveScalar]
    magnitudes: List[BCWaveMagnitude]
    provenance: str


def load_heat_bundle(heat_path: Path, magnitudes_path: Path) -> HeatBundle:
    heat_scalars = _load_heat_scalars(heat_path)
    magnitudes = _load_bc_magnitudes(magnitudes_path)
    return HeatBundle(
        heat_scalars=heat_scalars,
        magnitudes=magnitudes,
        provenance="reference/step1_dump_docs/part2_data/README_HEAT.md",
    )


def _load_heat_scalars(path: Path) -> List[HeatWaveScalar]:
    if not path.exists():
        raise HeatDataError(f"Heat table missing: {path}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        _require_columns(reader.fieldnames, {"league", "wave", "heat_scalar"}, path)
        rows: List[HeatWaveScalar] = []
        for idx, row in enumerate(reader, start=2):
            try:
                league = _require_field(row, "league", path)
                wave = int(_require_field(row, "wave", path))
                scalar = float(_require_field(row, "heat_scalar", path))
            except (ValueError, HeatDataError) as exc:
                raise HeatDataError(
                    f"Invalid heat row at line {idx}: {row}"
                ) from exc
            rows.append(HeatWaveScalar(league=league, wave=wave, scalar=scalar))
    if not rows:
        raise HeatDataError(f"Heat table empty: {path}")
    return rows


def _load_bc_magnitudes(path: Path) -> List[BCWaveMagnitude]:
    if not path.exists():
        raise HeatDataError(f"BC magnitudes table missing: {path}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        _require_columns(reader.fieldnames, {"bc_id", "league", "wave", "magnitude"}, path)
        rows: List[BCWaveMagnitude] = []
        for idx, row in enumerate(reader, start=2):
            try:
                bc_id = _require_field(row, "bc_id", path)
                league = _require_field(row, "league", path)
                wave = int(_require_field(row, "wave", path))
                magnitude = float(_require_field(row, "magnitude", path))
            except (ValueError, HeatDataError) as exc:
                raise HeatDataError(
                    f"Invalid BC magnitude row at line {idx}: {row}"
                ) from exc
            rows.append(
                BCWaveMagnitude(
                    bc_id=bc_id,
                    league=league,
                    wave=wave,
                    magnitude=magnitude,
                )
            )
    if not rows:
        raise HeatDataError(f"BC magnitudes table empty: {path}")
    return rows


def _require_columns(
    fieldnames: Iterable[str] | None, required: set[str], path: Path
) -> None:
    if fieldnames is None:
        raise HeatDataError(f"Missing header row in {path}")
    missing = required - set(fieldnames)
    if missing:
        raise HeatDataError(f"Missing columns {sorted(missing)} in {path}")


def _require_field(row: Dict[str, str], key: str, path: Path) -> str:
    if key not in row:
        raise HeatDataError(f"Missing {key!r} in row: {row} ({path})")
    value = row.get(key, "").strip()
    if value == "":
        raise HeatDataError(f"Empty {key!r} in row: {row} ({path})")
    return value
