from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tower_sim.loaders.table_paths import resolve_table_path
from typing import Iterable, List

from tower_sim.libs.step1_tables import TierBattleConditionRow, load_tier_battle_condition_rows


@dataclass(frozen=True)
class TierBattleCondition:
    tier: int
    name: str
    kind: str
    value: float | None
    unit: str | None
    notes: str

    @property
    def bc(self) -> str:
        return self.name


class TierBattleConditions:
    """
    Tier battle-conditions catalog.

    Source: tables/inputs/combat/tier_battle_conditions.csv
    (Effective Paths recovery, authoritative per user-supplied dump).

    Note: User-provided clarification confirms tiers 1–13 have no battle
    conditions; the catalog therefore begins at tier 14.
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
    parsed_rows = load_tier_battle_condition_rows(path)
    rows: List[TierBattleCondition] = []
    for idx, raw in enumerate(parsed_rows, start=2):
        try:
            condition = _convert_row(raw)
            if condition.value is None or condition.unit is None:
                raise ValueError("incomplete row")
        except ValueError as exc:
            if allow_incomplete:
                continue
            raise ValueError(
                f"Invalid tier battle condition row at line {idx}: {raw}"
            ) from exc
        rows.append(condition)
    return TierBattleConditions(rows)


def _convert_row(row: TierBattleConditionRow) -> TierBattleCondition:
    if row.kind.strip().upper() == "MISSING":
        return TierBattleCondition(
            tier=row.tier,
            name=row.bc,
            kind=row.kind,
            value=None,
            unit=None,
            notes=row.notes,
        )
    return TierBattleCondition(
        tier=row.tier,
        name=row.bc,
        kind=row.kind,
        value=row.value,
        unit=row.unit,
        notes=row.notes,
    )
