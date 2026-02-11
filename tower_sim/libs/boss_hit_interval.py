from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from tower_sim.loaders.table_paths import resolve_table_path
import csv
from typing import Dict, Mapping


class BossHitIntervalError(ValueError):
    pass


@dataclass(frozen=True)
class BossHitIntervalRow:
    hit_interval_id: str
    interval_seconds: float
    provenance: str


def boss_hit_interval_seconds(hit_interval_id: str) -> float:
    intervals = _load_intervals()
    key = hit_interval_id.strip()
    if key not in intervals:
        raise BossHitIntervalError(f"Unknown hit interval id: {hit_interval_id!r}.")
    interval = intervals[key].interval_seconds
    if interval <= 0:
        raise BossHitIntervalError(
            f"Hit interval must be > 0, got {interval} for id={hit_interval_id!r}."
        )
    return interval


@lru_cache(maxsize=1)
def _load_intervals() -> Mapping[str, BossHitIntervalRow]:
    table_path = resolve_table_path("boss_hit_interval")
    if not table_path.exists():
        raise BossHitIntervalError(f"Missing table: {table_path}")
    with table_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise BossHitIntervalError(f"Missing headers in table {table_path}")
        rows = [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
    intervals: Dict[str, BossHitIntervalRow] = {}
    for row in rows:
        hit_interval_id = row.get("hit_interval_id", "").strip()
        if not hit_interval_id:
            raise BossHitIntervalError("Hit interval table contains empty id.")
        interval_value = row.get("interval_seconds", "").strip()
        if interval_value == "":
            raise BossHitIntervalError(f"Missing interval_seconds for {hit_interval_id!r}.")
        if hit_interval_id in intervals:
            raise BossHitIntervalError(f"Duplicate hit interval id: {hit_interval_id!r}.")
        intervals[hit_interval_id] = BossHitIntervalRow(
            hit_interval_id=hit_interval_id,
            interval_seconds=float(interval_value),
            provenance=row.get("provenance", ""),
        )
    if not intervals:
        raise BossHitIntervalError("Hit interval table is empty.")
    return intervals


__all__ = ["BossHitIntervalError", "boss_hit_interval_seconds"]
