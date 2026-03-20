from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from tower_sim.loaders.table_paths import resolve_table_path


@dataclass(frozen=True)
class BattleConditionMagnitude:
    bc_id: str
    league: str
    wave: int
    magnitude: float


@dataclass(frozen=True)
class TournamentBossFrequency:
    league: str
    boss_every_n_waves: int


@dataclass(frozen=True)
class HeatWaveScalar:
    league: str
    wave: int
    heat_scalar: float


@dataclass(frozen=True)
class TierWaveDamageRow:
    tier: float
    wave: int
    wave_damage: float


@dataclass(frozen=True)
class TournamentWaveDamageRow:
    tournament_league: str
    wave: int
    wave_damage: float


@dataclass(frozen=True)
class TierBattleConditionRow:
    tier: int
    bc: str
    kind: str
    value: float | None
    unit: str | None
    notes: str


def load_battle_condition_magnitudes(
    path: Path | None = None,
) -> list[BattleConditionMagnitude]:
    csv_path = path or resolve_table_path("battle_condition_magnitudes")
    rows = _read_csv_rows(csv_path, {"bc_id", "league", "wave", "magnitude"})
    parsed: list[BattleConditionMagnitude] = []
    seen: set[tuple[str, str, int]] = set()
    for row in rows:
        bc_id = _require(row, "bc_id", csv_path)
        league = _require(row, "league", csv_path)
        wave = _parse_int(row, "wave", csv_path)
        magnitude = _parse_float(row, "magnitude", csv_path)
        key = (bc_id, league, wave)
        if key in seen:
            raise ValueError(f"Duplicate battle condition magnitude key {key} in {csv_path}")
        seen.add(key)
        parsed.append(
            BattleConditionMagnitude(
                bc_id=bc_id,
                league=league,
                wave=wave,
                magnitude=magnitude,
            )
        )
    if not parsed:
        raise ValueError(f"Battle condition magnitudes table is empty: {csv_path}")
    return parsed


def load_tournament_more_bosses_static(
    path: Path | None = None,
) -> list[TournamentBossFrequency]:
    csv_path = path or resolve_table_path("tournament_more_bosses_static")
    rows = _read_csv_rows(csv_path, {"league", "boss_every_n_waves"})
    parsed: list[TournamentBossFrequency] = []
    seen: set[str] = set()
    for row in rows:
        league = _require(row, "league", csv_path)
        boss_every = _parse_int(row, "boss_every_n_waves", csv_path)
        if league in seen:
            raise ValueError(f"Duplicate league {league!r} in {csv_path}")
        seen.add(league)
        parsed.append(
            TournamentBossFrequency(league=league, boss_every_n_waves=boss_every)
        )
    if not parsed:
        raise ValueError(f"Tournament boss frequency table is empty: {csv_path}")
    return parsed


def load_heat_wave_scalars(path: Path | None = None) -> list[HeatWaveScalar]:
    csv_path = path or resolve_table_path("heat_scale_long")
    rows = _read_csv_rows(csv_path, {"league", "wave", "heat_scalar"})
    parsed: list[HeatWaveScalar] = []
    seen: set[tuple[str, int]] = set()
    for row in rows:
        league = _require(row, "league", csv_path)
        wave = _parse_int(row, "wave", csv_path)
        heat_scalar = _parse_float(row, "heat_scalar", csv_path)
        key = (league, wave)
        if key in seen:
            raise ValueError(f"Duplicate heat wave key {key} in {csv_path}")
        seen.add(key)
        parsed.append(
            HeatWaveScalar(league=league, wave=wave, heat_scalar=heat_scalar)
        )
    if not parsed:
        raise ValueError(f"Heat wave scalar table is empty: {csv_path}")
    return parsed


def load_tier_wave_damage_rows(path: Path | None = None) -> list[TierWaveDamageRow]:
    csv_path = path or resolve_table_path("tier_wave_damage_legacy", runtime_mode=False)
    rows = _read_csv_rows(csv_path, {"tier", "wave", "wave_damage"})
    parsed: list[TierWaveDamageRow] = []
    seen: set[tuple[float, int]] = set()
    for row in rows:
        tier = _parse_float(row, "tier", csv_path)
        wave = _parse_int(row, "wave", csv_path)
        wave_damage = _parse_float(row, "wave_damage", csv_path)
        key = (tier, wave)
        if key in seen:
            raise ValueError(f"Duplicate tier wave damage key {key} in {csv_path}")
        seen.add(key)
        parsed.append(TierWaveDamageRow(tier=tier, wave=wave, wave_damage=wave_damage))
    if not parsed:
        raise ValueError(f"Tier wave damage table is empty: {csv_path}")
    return parsed


def load_tournament_wave_damage_rows(
    path: Path | None = None,
) -> list[TournamentWaveDamageRow]:
    csv_path = path or resolve_table_path("tournament_wave_damage_legacy", runtime_mode=False)
    rows = _read_csv_rows(csv_path, {"tournament_league", "wave", "wave_damage"})
    parsed: list[TournamentWaveDamageRow] = []
    seen: set[tuple[str, int]] = set()
    for row in rows:
        league = _require(row, "tournament_league", csv_path)
        wave = _parse_int(row, "wave", csv_path)
        wave_damage = _parse_float(row, "wave_damage", csv_path)
        key = (league, wave)
        if key in seen:
            raise ValueError(f"Duplicate tournament wave damage key {key} in {csv_path}")
        seen.add(key)
        parsed.append(
            TournamentWaveDamageRow(
                tournament_league=league,
                wave=wave,
                wave_damage=wave_damage,
            )
        )
    if not parsed:
        raise ValueError(f"Tournament wave damage table is empty: {csv_path}")
    return parsed


def load_tier_battle_condition_rows(
    path: Path | None = None,
) -> list[TierBattleConditionRow]:
    csv_path = path or resolve_table_path("tier_battle_conditions")
    rows = _read_csv_rows(
        csv_path, {"tier", "bc", "kind", "value", "unit", "notes"}
    )
    parsed: list[TierBattleConditionRow] = []
    seen: set[tuple[int, str, str]] = set()
    for row in rows:
        tier = _parse_int(row, "tier", csv_path)
        bc = _require(row, "bc", csv_path)
        kind = _require(row, "kind", csv_path)
        value_raw = row.get("value", "").strip()
        value = None
        if value_raw:
            value = _parse_float(row, "value", csv_path)
        unit = row.get("unit", "").strip() or None
        notes = row.get("notes", "").strip()
        key = (tier, bc, kind)
        if key in seen:
            raise ValueError(f"Duplicate tier battle condition key {key} in {csv_path}")
        seen.add(key)
        parsed.append(
            TierBattleConditionRow(
                tier=tier,
                bc=bc,
                kind=kind,
                value=value,
                unit=unit,
                notes=notes,
            )
        )
    if not parsed:
        raise ValueError(f"Tier battle condition table is empty: {csv_path}")
    return parsed


def load_dag_table(path: Path | None = None) -> dict:
    json_path = path or resolve_table_path("dag", runtime_mode=False)
    if not json_path.exists():
        raise FileNotFoundError(f"Missing DAG table: {json_path}")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"DAG table is not a JSON object: {json_path}")
    nodes = payload.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        raise ValueError(f"DAG table missing 'nodes' mapping: {json_path}")
    for name, node in nodes.items():
        if not isinstance(node, Mapping):
            raise ValueError(f"DAG node {name!r} is not a mapping in {json_path}")
        deps = node.get("deps")
        fn_name = node.get("fn_name")
        if not isinstance(deps, list) or not all(isinstance(dep, str) for dep in deps):
            raise ValueError(f"DAG node {name!r} has invalid deps in {json_path}")
        if not isinstance(fn_name, str) or not fn_name:
            raise ValueError(f"DAG node {name!r} missing fn_name in {json_path}")
    return payload


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
        rows = list(reader)
    return rows


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


def _parse_float(row: Mapping[str, str], key: str, path: Path) -> float:
    raw = _require(row, key, path)
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid {key} {raw!r} in {path}") from exc


__all__ = [
    "BattleConditionMagnitude",
    "HeatWaveScalar",
    "TierBattleConditionRow",
    "TierWaveDamageRow",
    "TournamentBossFrequency",
    "TournamentWaveDamageRow",
    "load_battle_condition_magnitudes",
    "load_dag_table",
    "load_heat_wave_scalars",
    "load_tier_battle_condition_rows",
    "load_tier_wave_damage_rows",
    "load_tournament_more_bosses_static",
    "load_tournament_wave_damage_rows",
]
