"""KB-driven v3 stat engine guardrail.

This module validates contributor-family -> canonical-stat routing using a
consolidated connection artifact, then delegates deterministic arithmetic to
TowerSim's common StatEngine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv

from tower_sim.engines.stat_engine import StatInput
from v3.stat_engine import V3StatEngine, V3StatEngineResult

from scripts.build_stat_connection_map import build_connection_rows, write_csv

_DEFAULT_CONNECTION_MAP_CSV = Path("out/stat_connection_map.csv")


class V3KBStatEngineError(RuntimeError):
    pass


@dataclass(frozen=True)
class StatConnectionMap:
    allowed_by_family: dict[str, set[str]]
    canonical_stats: set[str]


def _connection_map_from_rows(rows: list[dict[str, str]]) -> StatConnectionMap:
    allowed_by_family: dict[str, set[str]] = {}
    canonical_stats: set[str] = set()

    for row in rows:
        family = str(row.get("source_family") or "").strip()
        destination_object_type = str(row.get("destination_object_type") or "").strip()
        destination_id = str(row.get("destination_id") or "").strip()

        if family == "":
            raise V3KBStatEngineError("Connection map row missing source_family.")
        if destination_object_type == "":
            raise V3KBStatEngineError(f"Connection map row missing destination_object_type for family={family!r}.")
        if destination_id == "":
            raise V3KBStatEngineError(f"Connection map row missing destination_id for family={family!r}.")

        allowed = allowed_by_family.setdefault(family, set())
        if destination_object_type == "canonical_stat":
            allowed.add(destination_id)
            canonical_stats.add(destination_id)

    if not allowed_by_family:
        raise V3KBStatEngineError("Connection map produced no source families.")
    return StatConnectionMap(allowed_by_family=allowed_by_family, canonical_stats=canonical_stats)


def load_stat_connection_map_from_csv(csv_path: Path) -> StatConnectionMap:
    if not csv_path.exists():
        raise V3KBStatEngineError(f"Connection map CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [
            {
                "source_family": str(row.get("source_family") or ""),
                "destination_object_type": str(row.get("destination_object_type") or ""),
                "destination_id": str(row.get("destination_id") or ""),
            }
            for row in reader
        ]
    return _connection_map_from_rows(rows)


def load_stat_connection_map(*, csv_path: Path = _DEFAULT_CONNECTION_MAP_CSV, generate_if_missing: bool = True) -> StatConnectionMap:
    if csv_path.exists():
        return load_stat_connection_map_from_csv(csv_path)

    if not generate_if_missing:
        raise V3KBStatEngineError(f"Connection map CSV not found: {csv_path}")

    rows = build_connection_rows()
    write_csv(rows, csv_path)
    return _connection_map_from_rows(rows)


class V3KBStatEngine:
    def __init__(
        self,
        *,
        connection_map: StatConnectionMap | None = None,
        connection_map_csv: Path = _DEFAULT_CONNECTION_MAP_CSV,
        strict: bool = True,
    ) -> None:
        self._connection_map = connection_map or load_stat_connection_map(csv_path=connection_map_csv, generate_if_missing=True)
        self._strict = bool(strict)
        self._engine = V3StatEngine()

    def build(self, inputs: list[StatInput]) -> V3StatEngineResult:
        self._validate_inputs(inputs)
        return self._engine.build(inputs)

    def _validate_inputs(self, inputs: list[StatInput]) -> None:
        errors: list[str] = []
        for row in inputs:
            family = (row.contributor_family or "").strip()
            if family == "":
                errors.append(f"missing_contributor_family:{row.stat_id}")
                continue
            allowed_stats = self._connection_map.allowed_by_family.get(family)
            if allowed_stats is None:
                if self._strict:
                    errors.append(f"unknown_contributor_family:{family}:{row.stat_id}")
                continue
            # Only enforce KB routing for canonical stat surface.
            if row.stat_id in self._connection_map.canonical_stats and row.stat_id not in allowed_stats:
                if self._strict:
                    errors.append(f"kb_unwired:{family}:{row.stat_id}")

        if errors:
            raise V3KBStatEngineError("KB stat routing validation failed: " + ", ".join(sorted(set(errors))[:30]))
