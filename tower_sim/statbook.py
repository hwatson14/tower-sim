from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class StatRow:
    stat_id: str
    phase: str
    base_value: Optional[str]
    loadout_delta: Optional[str]
    enhancement_multiplier: Optional[str]
    tier_rule_delta_or_multiplier: Optional[str]
    final_value: Optional[str]
    provenance: Optional[str] = None


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
                        row.phase,
                        row.base_value if row.base_value is not None else "",
                        row.loadout_delta if row.loadout_delta is not None else "",
                        row.enhancement_multiplier
                        if row.enhancement_multiplier is not None
                        else "",
                        row.tier_rule_delta_or_multiplier
                        if row.tier_rule_delta_or_multiplier is not None
                        else "",
                        row.final_value if row.final_value is not None else "",
                        row.provenance if row.provenance is not None else "",
                    ]
                )

    def _sorted_rows(self) -> Iterable[StatRow]:
        return sorted(
            self.rows,
            key=lambda row: (row.stat_id, row.phase),
        )
