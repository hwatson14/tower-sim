from __future__ import annotations

from pathlib import Path
from tower_sim.libs.step1_tables import load_tier_battle_condition_rows
from tower_sim.loaders.tier_battle_conditions import TierBattleCondition


_DEFAULT_TIER_BC_PATH = Path(__file__).resolve().parents[2] / "tables" / "tier_battle_conditions.csv"


def load_tier_battle_conditions(
    path: Path | None = None,
) -> list[TierBattleCondition]:
    resolved = path or _DEFAULT_TIER_BC_PATH
    rows = load_tier_battle_condition_rows(resolved)
    parsed = [
        TierBattleCondition(
            tier=row.tier,
            name=row.bc,
            kind=row.kind,
            value=row.value,
            unit=row.unit,
            notes=row.notes,
        )
        for row in rows
    ]
    if not parsed:
        raise ValueError(f"Tier battle condition table is empty: {resolved}.")
    return parsed


def tier_battle_conditions_for_tier(
    tier: int,
    path: Path | None = None,
) -> list[TierBattleCondition]:
    rows = load_tier_battle_conditions(path)
    return [row for row in rows if row.tier == tier]
