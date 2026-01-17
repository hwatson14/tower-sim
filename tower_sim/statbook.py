from __future__ import annotations

from dataclasses import dataclass, field
import csv
from pathlib import Path
from typing import Iterable, List, Optional

from tower_sim.stat_registry import Phase, StatDef, StatRegistry, UnknownStatError, default_registry


@dataclass(frozen=True)
class StatRow:
    stat_id: str
    phase: Phase
    value: Optional[str]
    source: str
    notes: Optional[str] = None


@dataclass(frozen=True)
class StatBook:
    rows: List[StatRow]
    registry: StatRegistry = field(default_factory=default_registry)

    def __post_init__(self) -> None:
        for row in self.rows:
            self._validate_row(row)

    def add_row(self, row: StatRow) -> "StatBook":
        self._validate_row(row)
        return StatBook(rows=[*self.rows, row], registry=self.registry)

    def to_csv(self, path: Path) -> Path:
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["stat_id", "phase", "value", "source", "notes"])
            for row in self._sorted_rows():
                writer.writerow(
                    [
                        row.stat_id,
                        row.phase.value,
                        row.value if row.value is not None else "",
                        row.source,
                        row.notes if row.notes is not None else "",
                    ]
                )
        definitions_path = path.with_suffix(".definitions.csv")
        self.to_definitions_csv(definitions_path)
        return definitions_path

    def to_definitions_csv(self, path: Path) -> None:
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "stat_id",
                    "display_name",
                    "unit",
                    "kind",
                    "scope",
                    "allowed_phases",
                    "description",
                ]
            )
            for definition in self.registry.all_defs():
                writer.writerow(
                    [
                        definition.stat_id,
                        definition.display_name,
                        definition.unit.value,
                        definition.kind.value,
                        definition.scope.value,
                        "|".join(sorted(phase.value for phase in definition.allowed_phases)),
                        definition.description or "",
                    ]
                )

    def _sorted_rows(self) -> Iterable[StatRow]:
        return sorted(
            self.rows,
            key=lambda row: (row.stat_id, row.phase.value, row.source),
        )

    def _validate_row(self, row: StatRow) -> None:
        try:
            stat_def = self.registry.get(row.stat_id)
        except UnknownStatError as exc:
            raise UnknownStatError(
                f"Unknown stat_id in StatBook row: {row.stat_id} (phase={row.phase.value})"
            ) from exc
        if row.phase not in stat_def.allowed_phases:
            raise UnknownStatError(
                f"Phase {row.phase.value} not allowed for stat_id {row.stat_id}."
            )
