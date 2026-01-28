from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class CardTable:
    rarity: str
    name: str
    levels: Dict[int, str]


def _read_csv(path: Path) -> list[list[str]]:
    with path.open(newline="") as handle:
        return list(csv.reader(handle))


def load_cards_tables(cache_dir: Path = Path("tower_sim/wiki/cache")) -> Dict[str, CardTable]:
    tables: Dict[str, CardTable] = {}
    for path in sorted(cache_dir.glob("cards_*.csv")):
        rows = _read_csv(path)
        if not rows:
            continue
        header = [cell.strip() for cell in rows[0]]
        level_columns = {
            idx: int(col.replace("Lv.", "").strip())
            for idx, col in enumerate(header)
            if col.startswith("Lv.")
        }
        for row in rows[1:]:
            if len(row) < 2:
                continue
            rarity = row[0].strip()
            name = row[1].strip()
            if not name:
                continue
            levels: Dict[int, str] = {}
            for idx, level in level_columns.items():
                if idx >= len(row):
                    continue
                value = row[idx].strip()
                if value == "":
                    continue
                levels[level] = value
            tables[f"{rarity}:{name}"] = CardTable(rarity=rarity, name=name, levels=levels)
    return tables


def card_value(card_name: str, level: int, tables: Dict[str, CardTable]) -> str:
    matching = [table for table in tables.values() if table.name == card_name]
    if not matching:
        raise KeyError(f"Card not found: {card_name!r}")
    if len(matching) > 1:
        raise KeyError(f"Card name ambiguous without rarity: {card_name!r}")
    table = matching[0]
    if level not in table.levels:
        raise KeyError(f"Card level {level} missing for {card_name!r}")
    return table.levels[level]


def card_value_by_rarity(
    card_name: str,
    rarity: str,
    level: int,
    tables: Dict[str, CardTable],
) -> str:
    key = f"{rarity}:{card_name}"
    if key not in tables:
        raise KeyError(f"Card not found: {card_name!r} ({rarity!r})")
    table = tables[key]
    if level not in table.levels:
        raise KeyError(f"Card level {level} missing for {card_name!r} ({rarity!r})")
    return table.levels[level]
