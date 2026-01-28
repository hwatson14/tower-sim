from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
import csv


@dataclass(frozen=True)
class TierBattleCondition:
    tier: int
    name: str
    kind: str
    value: float
    unit: str
    notes: str


class TierBattleConditions:
    """
    Tier battle-conditions catalog.

    Source: reference/step1_dump_docs/part2_data/tier14_21_battle_conditions.csv
    (Effective Paths recovery, authoritative per user-supplied dump).
    """

    def __init__(self, rows: Iterable[TierBattleCondition]) -> None:
        self._rows = list(rows)

    @property
    def rows(self) -> List[TierBattleCondition]:
        return list(self._rows)

    def for_tier(self, tier: int) -> List[TierBattleCondition]:
        return [row for row in self._rows if row.tier == tier]


def load_tier_battle_conditions(
    path: Path, *, allow_incomplete: bool = False
) -> TierBattleConditions:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows: List[TierBattleCondition] = []
        for idx, raw in enumerate(reader, start=2):
            try:
                tier = int(raw["tier"])
                value_raw = raw.get("value", "").strip()
                if value_raw == "" or raw.get("kind", "").strip().upper() == "MISSING":
                    raise ValueError("incomplete row")
                value = float(value_raw)
            except (KeyError, ValueError) as exc:
                if allow_incomplete:
                    continue
                raise ValueError(
                    f"Invalid tier battle condition row at line {idx}: {raw}"
                ) from exc
            rows.append(
                TierBattleCondition(
                    tier=tier,
                    name=raw.get("bc", "").strip(),
                    kind=raw.get("kind", "").strip(),
                    value=value,
                    unit=raw.get("unit", "").strip(),
                    notes=raw.get("notes", "").strip(),
                )
            )
    return TierBattleConditions(rows)
