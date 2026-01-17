from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

from tower_sim.libs.data_paths import resolve_data_file


@dataclass(frozen=True)
class WorkshopTables:
    wsvalues: Dict[str, Dict[int, str]]
    dvt_sections: Dict[str, Dict[str, Dict[int, str]]]


def _read_csv(path: Path) -> list[list[str]]:
    with path.open(newline="") as handle:
        return list(csv.reader(handle))


def _parse_wsvalues(rows: list[list[str]]) -> Dict[str, Dict[int, str]]:
    if not rows:
        return {}
    header = rows[0]
    tables: Dict[str, Dict[int, str]] = {}
    col = 0
    while col + 1 < len(header):
        level_header = header[col].strip()
        stat_name = header[col + 1].strip()
        if level_header == "Level" and stat_name:
            tables.setdefault(stat_name, {})
            for row in rows[1:]:
                if col >= len(row) or col + 1 >= len(row):
                    continue
                level_str = row[col].strip()
                value = row[col + 1].strip()
                if level_str == "" or value == "":
                    continue
                tables[stat_name][int(level_str)] = value
        col += 2
    return tables


def _parse_dvt_workshop(rows: list[list[str]]) -> Dict[str, Dict[str, Dict[int, str]]]:
    if not rows:
        return {}
    header = rows[0]
    blank_indices = [idx for idx, cell in enumerate(header) if cell.strip() == ""]
    if not blank_indices:
        raise ValueError("DVT_Workshop.csv missing section separators in header row.")
    blank_indices.append(len(header))
    groups: list[tuple[int, int]] = []
    for start, end in zip(blank_indices, blank_indices[1:]):
        if end - start <= 1:
            continue
        groups.append((start, end))
    sections: Dict[str, Dict[str, Dict[int, str]]] = {}
    current_sections: Dict[int, Optional[str]] = {start: None for start, _ in groups}
    section_levels: Dict[tuple[int, str], int] = {}
    for row in rows[1:]:
        for start, end in groups:
            label_cell = row[start].strip() if start < len(row) else ""
            if label_cell:
                current_sections[start] = label_cell
                section_levels.setdefault((start, label_cell), 0)
            current_section = current_sections[start]
            if current_section is None:
                continue
            values = row[start + 1 : min(end, len(row))]
            if not any(cell.strip() for cell in values):
                continue
            level = section_levels[(start, current_section)]
            for idx in range(start + 1, min(end, len(header))):
                stat_name = header[idx].strip()
                if not stat_name:
                    continue
                value = row[idx].strip() if idx < len(row) else ""
                if value == "":
                    continue
                sections.setdefault(current_section, {}).setdefault(stat_name, {})[level] = value
            section_levels[(start, current_section)] = level + 1
    return sections


def load_workshop_tables(
    wsvalues_path: Optional[Path] = None,
    dvt_path: Optional[Path] = None,
) -> WorkshopTables:
    wsvalues_file = wsvalues_path or resolve_data_file("WSValues.csv")
    dvt_file = dvt_path or resolve_data_file("DVT_Workshop.csv")
    wsvalues_rows = _read_csv(wsvalues_file)
    dvt_rows = _read_csv(dvt_file)
    return WorkshopTables(
        wsvalues=_parse_wsvalues(wsvalues_rows),
        dvt_sections=_parse_dvt_workshop(dvt_rows),
    )


def workshop_value(
    stat_key: str,
    level: int,
    tables: WorkshopTables,
    section: str = "WSValues",
) -> str:
    if section == "WSValues":
        if stat_key not in tables.wsvalues:
            raise KeyError(f"WSValues missing stat {stat_key!r}.")
        stat_table = tables.wsvalues[stat_key]
        if level not in stat_table:
            raise KeyError(f"WSValues missing level {level} for {stat_key!r}.")
        return stat_table[level]
    if section not in tables.dvt_sections:
        raise KeyError(f"DVT_Workshop missing section {section!r}.")
    if stat_key not in tables.dvt_sections[section]:
        raise KeyError(f"DVT_Workshop missing stat {stat_key!r} in section {section!r}.")
    stat_table = tables.dvt_sections[section][stat_key]
    if level not in stat_table:
        raise KeyError(f"DVT_Workshop missing level {level} for {stat_key!r} in {section!r}.")
    return stat_table[level]
