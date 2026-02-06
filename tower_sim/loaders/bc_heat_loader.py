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


@dataclass(frozen=True)
class TournamentHeatValue:
    league: str
    wave_actual: int
    bc_key: str
    bc_variant: str
    bc_id: str
    value_raw: str
    value_num: float
    value_unit: str
    value_kind: str


@dataclass(frozen=True)
class TournamentHeatRegistryRow:
    bc_key: str
    bc_variant: str
    bc_id: str
    value_unit: str
    value_kind: str
    applies_champion: bool
    applies_legend: bool


def make_bc_id(bc_key: str, bc_variant: str) -> str:
    return f"{bc_key}:{bc_variant}"


class TournamentHeatTable:
    def __init__(
        self,
        *,
        values: List[TournamentHeatValue],
        registry: List[TournamentHeatRegistryRow],
        provenance: str,
    ) -> None:
        self.values = values
        self.registry = registry
        self.provenance = provenance
        self._index: Dict[tuple[str, str], List[TournamentHeatValue]] = {}
        for row in values:
            self._index.setdefault((row.league, row.bc_id), []).append(row)
        for rows in self._index.values():
            rows.sort(key=lambda r: r.wave_actual)

    def value_at(self, *, league: str, wave_actual: int, bc_id: str) -> TournamentHeatValue:
        league_key = league.strip().lower()
        if league_key not in {"champion", "legend"}:
            raise HeatDataError(f"Unsupported tournament league: {league!r}")
        key = (league_key, bc_id)
        if key not in self._index:
            raise HeatDataError(f"Unknown tournament bc_id for league {league_key!r}: {bc_id!r}")
        rows = self._index[key]
        min_wave = rows[0].wave_actual
        max_wave = rows[-1].wave_actual
        if wave_actual < min_wave or wave_actual > max_wave:
            raise HeatDataError(
                f"wave_actual {wave_actual} outside coverage for {league_key}/{bc_id}: [{min_wave}, {max_wave}]"
            )
        current = rows[0]
        for row in rows:
            if row.wave_actual <= wave_actual:
                current = row
            else:
                break
        return current


def load_heat_bundle(heat_path: Path, magnitudes_path: Path) -> HeatBundle:
    heat_scalars = _load_heat_scalars(heat_path)
    magnitudes = _load_bc_magnitudes(magnitudes_path)
    return HeatBundle(
        heat_scalars=heat_scalars,
        magnitudes=magnitudes,
        provenance="reference/step1_dump_docs/part2_data/README_HEAT.md",
    )


def load_tournament_heat_table(
    scale_path: Path,
    registry_path: Path,
) -> TournamentHeatTable:
    values = _load_tournament_heat_values(scale_path)
    registry = _load_tournament_heat_registry(registry_path)
    registry_by_league = {
        "champion": {r.bc_id for r in registry if r.applies_champion},
        "legend": {r.bc_id for r in registry if r.applies_legend},
    }
    scale_by_league: Dict[str, set[str]] = {"champion": set(), "legend": set()}
    for row in values:
        if row.league not in scale_by_league:
            continue
        scale_by_league[row.league].add(row.bc_id)
    required_bc_ids = {"more_bosses:", "death_defy_down:", "energy_shields_down:"}
    for league in ("champion", "legend"):
        missing_registry = sorted(required_bc_ids - registry_by_league[league])
        if missing_registry:
            raise HeatDataError(f"Missing required BC ids in registry for {league}: {missing_registry}")
        missing_scale = sorted(required_bc_ids - scale_by_league[league])
        if missing_scale:
            raise HeatDataError(f"Missing required BC ids in heat table for {league}: {missing_scale}")

    for league in ("champion", "legend"):
        missing = sorted(scale_by_league[league] - registry_by_league[league])
        if missing:
            raise HeatDataError(f"Missing BC ids in registry for {league}: {missing}")

    return TournamentHeatTable(
        values=values,
        registry=registry,
        provenance="tables/heat_scale_long.csv + tables/heat_bc_registry.csv",
    )


def _parse_bool(value: str) -> bool:
    norm = value.strip().lower()
    if norm in {"true", "1", "yes"}:
        return True
    if norm in {"false", "0", "no"}:
        return False
    raise HeatDataError(f"Invalid boolean value: {value!r}")


def _load_tournament_heat_registry(path: Path) -> List[TournamentHeatRegistryRow]:
    if not path.exists():
        raise HeatDataError(f"Tournament heat BC registry missing: {path}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        _require_columns(
            reader.fieldnames,
            {"bc_key", "bc_variant", "value_unit", "value_kind", "applies_champion", "applies_legend"},
            path,
        )
        rows: List[TournamentHeatRegistryRow] = []
        for idx, row in enumerate(reader, start=2):
            try:
                bc_key = _require_field(row, "bc_key", path)
                bc_variant = row.get("bc_variant", "").strip()
                value_kind = _require_field(row, "value_kind", path)
                if value_kind.strip().lower() == "unknown":
                    raise HeatDataError("value_kind cannot be 'unknown'")
                rows.append(
                    TournamentHeatRegistryRow(
                        bc_key=bc_key,
                        bc_variant=bc_variant,
                        bc_id=make_bc_id(bc_key, bc_variant),
                        value_unit=_require_field(row, "value_unit", path),
                        value_kind=value_kind,
                        applies_champion=_parse_bool(_require_field(row, "applies_champion", path)),
                        applies_legend=_parse_bool(_require_field(row, "applies_legend", path)),
                    )
                )
            except HeatDataError as exc:
                raise HeatDataError(f"Invalid tournament registry row at line {idx}: {row}") from exc
    if not rows:
        raise HeatDataError(f"Tournament heat BC registry empty: {path}")
    return rows


def _load_tournament_heat_values(path: Path) -> List[TournamentHeatValue]:
    if not path.exists():
        raise HeatDataError(f"Tournament heat scale table missing: {path}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        _require_columns(
            reader.fieldnames,
            {"league", "wave_actual", "bc_key", "bc_variant", "value_raw", "value_num", "value_unit", "value_kind"},
            path,
        )
        rows: List[TournamentHeatValue] = []
        for idx, row in enumerate(reader, start=2):
            try:
                league = _require_field(row, "league", path).lower()
                if league not in {"champion", "legend"}:
                    raise HeatDataError(f"Unsupported league in heat scale: {league!r}")
                bc_key = _require_field(row, "bc_key", path)
                bc_variant = row.get("bc_variant", "").strip()
                value_kind = _require_field(row, "value_kind", path)
                if value_kind.strip().lower() == "unknown":
                    raise HeatDataError("value_kind cannot be 'unknown'")
                rows.append(
                    TournamentHeatValue(
                        league=league,
                        wave_actual=int(_require_field(row, "wave_actual", path)),
                        bc_key=bc_key,
                        bc_variant=bc_variant,
                        bc_id=make_bc_id(bc_key, bc_variant),
                        value_raw=_require_field(row, "value_raw", path),
                        value_num=float(_require_field(row, "value_num", path)),
                        value_unit=_require_field(row, "value_unit", path),
                        value_kind=value_kind,
                    )
                )
            except (ValueError, HeatDataError) as exc:
                raise HeatDataError(f"Invalid tournament heat scale row at line {idx}: {row}") from exc
    if not rows:
        raise HeatDataError(f"Tournament heat scale table empty: {path}")
    return rows


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
                raise HeatDataError(f"Invalid heat row at line {idx}: {row}") from exc
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
                raise HeatDataError(f"Invalid BC magnitude row at line {idx}: {row}") from exc
            rows.append(BCWaveMagnitude(bc_id=bc_id, league=league, wave=wave, magnitude=magnitude))
    if not rows:
        raise HeatDataError(f"BC magnitudes table empty: {path}")
    return rows


def _require_columns(fieldnames: Iterable[str] | None, required: set[str], path: Path) -> None:
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
