"""
input/ids_parser.py — IDS CSV parsing. AUTHORITY for all IDS parsing logic.

Owns: IDS section-spec layout, CSV read, section slicing, header validation,
parse_ids() public entry point returning IdsRaw.

Legacy path (parsers/ids_parser.py) is a backward-compat shim that re-exports
from here. It will be demoted to archive/legacy/ in T8.

"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

@dataclass(frozen=True)
class IdsRaw:
    ids_path: Path
    header: List[str]
    raw_sections: Dict[str, List[List[str]]]
    section_headers: Dict[str, List[str]]


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

_SECTION_SPEC_BY_NAME = {spec.name: spec for spec in SECTION_SPECS}
_SECTION_ORDER = [spec.name for spec in SECTION_SPECS]


IDS_HEADER_ALLOWLIST = {
    "exact": {"?", "Cards Presets"},
    "prefixes": ("http",),
}

IDS_HEADER_ERROR_PLACEHOLDERS = {"#REF!"}

_IDS_VERSION_TOKEN_RE = re.compile(r"^v\d+(\.\d+)*$")


def _read_csv_rows(path: Path) -> List[List[str]]:
    with path.open(newline="", encoding='utf-8-sig') as handle:
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


def _section_specs_for_header(header: List[str]) -> List[SectionSpec]:
    specs: List[SectionSpec] = []
    last_header_col = -1
    for name in _SECTION_ORDER:
        try:
            header_col = next(idx for idx, value in enumerate(header) if value.strip() == name)
        except StopIteration as exc:
            expected = _SECTION_SPEC_BY_NAME[name]
            raise ValueError(
                f"Missing section header for {name!r}; expected near column {expected.header_col}."
            ) from exc
        if header_col <= last_header_col:
            raise ValueError(
                "Unexpected section header order in _IDS.csv: "
                f"{name!r} found at column {header_col} after column {last_header_col}."
            )
        base = _SECTION_SPEC_BY_NAME[name]
        start_col = header_col + (base.start_col - base.header_col)
        specs.append(SectionSpec(name, header_col, start_col, len(header) - 1))
        last_header_col = header_col
    for idx, spec in enumerate(specs[:-1]):
        specs[idx] = SectionSpec(spec.name, spec.header_col, spec.start_col, specs[idx + 1].header_col - 1)
    return specs


def _fail_unknown_sections(rows: List[List[str]]) -> None:
    header = rows[0] if rows else []
    specs = _section_specs_for_header(header)
    known = {spec.name for spec in specs}
    known_header_width = max(spec.end_col for spec in specs) + 1
    cards_spec = next(spec for spec in specs if spec.name == "Cards")
    for idx, cell in enumerate(header):
        value = cell.strip()
        if value == "" or value in known:
            continue
        if value in IDS_HEADER_ALLOWLIST["exact"]:
            continue
        if value in IDS_HEADER_ERROR_PLACEHOLDERS and idx < known_header_width:
            continue
        if any(value.startswith(prefix) for prefix in IDS_HEADER_ALLOWLIST["prefixes"]):
            continue
        if _IDS_VERSION_TOKEN_RE.fullmatch(value):
            continue
        row_values = rows[1] if len(rows) > 1 else []
        offending = row_values[idx] if idx < len(row_values) else ""
        if cards_spec.start_col <= idx <= cards_spec.end_col and value.isdigit() and offending.strip().startswith("Preset"):
            continue
        raise ValueError(
            "Unknown section header in _IDS.csv: "
            f"{value!r} at column {idx}. First row value: {offending!r}"
        )


def parse_ids(path: Path) -> IdsRaw:
    """Parse an IDS CSV file and return an IdsRaw containing all sections."""
    rows = _read_csv_rows(path)
    if not rows:
        raise ValueError(f"_IDS.csv is empty: {path}")
    _fail_unknown_sections(rows)
    raw_sections: Dict[str, List[List[str]]] = {}
    section_headers: Dict[str, List[str]] = {}
    for spec in _section_specs_for_header(rows[0]):
        raw_sections[spec.name] = _collect_section_rows(rows, spec)
        section_headers[spec.name] = _slice_row(rows[0], spec.start_col, spec.end_col)
    return IdsRaw(ids_path=path, header=rows[0], raw_sections=raw_sections, section_headers=section_headers)


__all__ = ["IdsRaw", "parse_ids", "SectionSpec", "SECTION_SPECS"]
