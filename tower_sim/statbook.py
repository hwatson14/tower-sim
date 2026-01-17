from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class StatRow:
    stat_name: str
    phase: str
    value: Optional[str]
    source: str
    notes: Optional[str] = None


@dataclass(frozen=True)
class StatBook:
    rows: List[StatRow]

    def to_csv(self, path: Path) -> None:
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["stat_name", "phase", "value", "source", "notes"])
            for row in self._sorted_rows():
                writer.writerow(
                    [
                        row.stat_name,
                        row.phase,
                        row.value if row.value is not None else "",
                        row.source,
                        row.notes if row.notes is not None else "",
                    ]
                )

    def _sorted_rows(self) -> Iterable[StatRow]:
        return sorted(
            self.rows,
            key=lambda row: (row.stat_name, row.phase, row.source),
        )
