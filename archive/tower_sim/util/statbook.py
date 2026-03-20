from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import csv
from pathlib import Path
from typing import Iterable, List, Optional

from tower_sim.registry.stat_registry import Phase


@dataclass(frozen=True)
class StatRow:
    stat_id: str
    phase: Phase
    base_value: Optional[Decimal]
    loadout_delta_modules: Optional[Decimal]
    loadout_delta_cards: Optional[Decimal]
    loadout_delta_bots: Optional[Decimal]
    loadout_delta_guardians: Optional[Decimal]
    loadout_delta_other: Optional[Decimal]
    enhancement_multiplier: Optional[Decimal]
    tier_rule_delta_or_multiplier: Optional[Decimal]
    final_value: Optional[Decimal]
    provenance: str

    def loadout_delta_total(self) -> Optional[Decimal]:
        components = [
            self.loadout_delta_modules,
            self.loadout_delta_cards,
            self.loadout_delta_bots,
            self.loadout_delta_guardians,
            self.loadout_delta_other,
        ]
        if all(component is None for component in components):
            return None
        if any(component is None for component in components):
            raise ValueError(
                "All loadout delta components must be provided when any are set."
            )
        return sum(components, Decimal(0))


@dataclass(frozen=True)
class StatBook:
    rows: List[StatRow]

    def to_csv(self, path: Path) -> None:
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "stat_id",
                    "phase",
                    "base_value",
                    "loadout_delta",
                    "loadout_delta_modules",
                    "loadout_delta_cards",
                    "loadout_delta_bots",
                    "loadout_delta_guardians",
                    "loadout_delta_other",
                    "enhancement_multiplier",
                    "tier_rule_delta_or_multiplier",
                    "final_value",
                    "provenance",
                ]
            )
            for row in self._sorted_rows():
                writer.writerow(
                    [
                        row.stat_id,
                        row.phase.value,
                        _format_decimal(row.base_value),
                        _format_decimal(row.loadout_delta_total()),
                        _format_decimal(row.loadout_delta_modules),
                        _format_decimal(row.loadout_delta_cards),
                        _format_decimal(row.loadout_delta_bots),
                        _format_decimal(row.loadout_delta_guardians),
                        _format_decimal(row.loadout_delta_other),
                        _format_decimal(row.enhancement_multiplier),
                        _format_decimal(row.tier_rule_delta_or_multiplier),
                        _format_decimal(row.final_value),
                        row.provenance,
                    ]
                )

    def _sorted_rows(self) -> Iterable[StatRow]:
        return sorted(
            self.rows,
            key=lambda row: (row.stat_id.startswith("uw_"), row.stat_id, row.phase.value, row.provenance),
        )


# Backward-compatible aliases during migration to canonical-only schema naming.
CanonicalStatRow = StatRow
CanonicalStatBook = StatBook


def _format_decimal(value: Optional[Decimal]) -> str:
    if value is None:
        return ""
    return format(value, "f")
