from __future__ import annotations

from dataclasses import dataclass
import csv
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from tower_sim.util.ids_raw import IdsRaw


@dataclass(frozen=True)
class SectionSpec:
    name: str
    header_col: int
    start_col: int
    end_col: int


SECTION_SPECS = [
    SectionSpec("Labs", 0, 0, 3),
    SectionSpec("WS", 4, 5, 16),
    SectionSpec("WS+", 17, 17, 24),
    SectionSpec("UWs", 25, 25, 29),
    SectionSpec("Cards", 30, 30, 37),
    SectionSpec("Relics", 38, 38, 40),
    SectionSpec("Vault", 41, 41, 42),
    SectionSpec("Bots", 44, 44, 48),
    SectionSpec("Themes & Songs", 50, 50, 51),
    SectionSpec("Modules", 53, 53, 71),
    SectionSpec("Guardians", 72, 72, 76),
    SectionSpec("Player & Stuff", 77, 77, 82),
]


DEFAULT_IDS_PATHS: Sequence[Path] = (
    Path("tests/fixtures/tower-sim-data/_IDS.csv"),
)


def resolve_ids_path(paths: Sequence[Path] = DEFAULT_IDS_PATHS) -> Path:
    for path in paths:
        if path.exists():
            return path
    candidates = ", ".join(str(path) for path in paths)
    raise FileNotFoundError(f"Could not find _IDS.csv. Tried: {candidates}")


def _read_csv_rows(path: Path) -> List[List[str]]:
    with path.open(newline="") as handle:
        return list(csv.reader(handle))


def _slice_row(row: List[str], start: int, end: int) -> List[str]:
    padded = row + [""] * max(0, end + 1 - len(row))
    return padded[start : end + 1]


def _row_has_data(row: List[str]) -> bool:
    return any(cell.strip() != "" for cell in row)


def _collect_section_rows(rows: List[List[str]], spec: SectionSpec) -> List[List[str]]:
    out: List[List[str]] = []
    for row in rows[1:]:
        sliced = _slice_row(row, spec.start_col, spec.end_col)
        if _row_has_data(sliced):
            out.append(sliced)
    return out


def _fail_unknown_sections(rows: List[List[str]]) -> None:
    header = rows[0] if rows else []
    known = {spec.name for spec in SECTION_SPECS}
    allowed_metadata = {""}
    cards_spec = next(spec for spec in SECTION_SPECS if spec.name == "Cards")
    for spec in SECTION_SPECS:
        if spec.header_col >= len(header):
            raise ValueError(
                f"Missing section header for {spec.name!r} at column {spec.header_col}."
            )
        if header[spec.header_col].strip() != spec.name:
            raise ValueError(
                "Unexpected section header location in _IDS.csv: "
                f"expected {spec.name!r} at column {spec.header_col}, "
                f"found {header[spec.header_col]!r}."
            )
    for idx, cell in enumerate(header):
        value = cell.strip()
        if value == "":
            continue
        if value in known or value in allowed_metadata:
            continue
        if value.startswith("http") or value == "?" or value.startswith("v"):
            continue
        if value == "Cards Presets":
            continue
        row_values = rows[1] if len(rows) > 1 else []
        offending = row_values[idx] if idx < len(row_values) else ""
        if (
            cards_spec.start_col <= idx <= cards_spec.end_col
            and value.isdigit()
            and offending.strip().startswith("Preset")
        ):
            continue
        raise ValueError(
            "Unknown section header in _IDS.csv: "
            f"{value!r} at column {idx}. First row value: {offending!r}"
        )


def parse_ids(path: Optional[Path] = None) -> IdsRaw:
    ids_path = path or resolve_ids_path()
    rows = _read_csv_rows(ids_path)
    if not rows:
        raise ValueError(f"_IDS.csv is empty: {ids_path}")
    _fail_unknown_sections(rows)
    raw_sections: Dict[str, List[List[str]]] = {}
    for spec in SECTION_SPECS:
        raw_sections[spec.name] = _collect_section_rows(rows, spec)
    return IdsRaw(ids_path=ids_path, header=rows[0], raw_sections=raw_sections)
