from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
import csv
import re
from typing import Dict, Iterable, List, Mapping

from tower_sim.loaders.table_paths import resolve_table_path


class ModuleMainEffectError(ValueError):
    pass


@dataclass(frozen=True)
class BaseBonusRow:
    cannon: float
    armor: float
    generator: float
    core: float


@dataclass(frozen=True)
class BandRow:
    start: int
    end: int
    cannon_inc: float
    armor_inc: float
    generator_inc: float
    core_inc: float


def module_main_effect_multiplier(slot: str, rarity: str, level: int) -> float:
    base_bonuses = _load_base_bonuses()
    bands = _load_bands()
    if rarity not in base_bonuses:
        raise ModuleMainEffectError(f"Unknown rarity {rarity!r}.")
    if level < 0:
        raise ModuleMainEffectError("Module level cannot be negative.")
    slot_key = slot.strip().lower()
    base = base_bonuses[rarity]
    base_bonus = _slot_value(base, slot_key)
    level_bonus = _level_bonus(level, bands, slot_key)
    star_mult = _star_multiplier(rarity)
    result = (Decimal(str(base_bonus)) + Decimal(str(level_bonus))) * Decimal(
        str(star_mult)
    ) + Decimal("1")
    return float(_round_half_up(result, 3))


def _slot_value(base: BaseBonusRow, slot_key: str) -> float:
    if slot_key == "cannon":
        return base.cannon
    if slot_key == "armor":
        return base.armor
    if slot_key == "generator":
        return base.generator
    if slot_key == "core":
        return base.core
    raise ModuleMainEffectError(f"Unknown module slot {slot_key!r}.")


def _level_bonus(level: int, bands: Iterable[BandRow], slot_key: str) -> float:
    bonus = Decimal("0")
    for band in bands:
        start = band.start
        end = band.end
        if level > end:
            levels_in_band = end - start
        elif level < start:
            levels_in_band = 0
        else:
            levels_in_band = level - start
        inc = Decimal(str(_band_inc(band, slot_key)))
        bonus += Decimal(levels_in_band) * inc
    return float(bonus)


def _band_inc(band: BandRow, slot_key: str) -> float:
    if slot_key == "cannon":
        return band.cannon_inc
    if slot_key == "armor":
        return band.armor_inc
    if slot_key == "generator":
        return band.generator_inc
    if slot_key == "core":
        return band.core_inc
    raise ModuleMainEffectError(f"Unknown module slot {slot_key!r}.")


_STAR_RE = re.compile(r"(?P<count>\d)\*$")


def _star_multiplier(rarity: str) -> float:
    match = _STAR_RE.search(rarity.strip())
    if match is None:
        return 1.0
    count = int(match.group("count"))
    return 1.0 + (count * 0.04)


def _round_half_up(value: Decimal, places: int) -> Decimal:
    quant = Decimal("1").scaleb(-places)
    return value.quantize(quant, rounding=ROUND_HALF_UP)


@lru_cache(maxsize=1)
def _load_base_bonuses() -> Mapping[str, BaseBonusRow]:
    rows = _load_csv(resolve_table_path("module_main_effect_bases"))
    result: Dict[str, BaseBonusRow] = {}
    for row in rows:
        rarity = row["rarity"]
        result[rarity] = BaseBonusRow(
            cannon=float(row["cannon_base"]),
            armor=float(row["armor_base"]),
            generator=float(row["generator_base"]),
            core=float(row["core_base"]),
        )
    if not result:
        raise ModuleMainEffectError("Base bonus table is empty.")
    return result


@lru_cache(maxsize=1)
def _load_bands() -> List[BandRow]:
    rows = _load_csv(resolve_table_path("module_main_effect_bands"))
    bands: List[BandRow] = []
    for row in rows:
        bands.append(
            BandRow(
                start=int(float(row["start_level"])),
                end=int(float(row["end_level"])),
                cannon_inc=float(row["cannon_inc"]),
                armor_inc=float(row["armor_inc"]),
                generator_inc=float(row["generator_inc"]),
                core_inc=float(row["core_inc"]),
            )
        )
    if not bands:
        raise ModuleMainEffectError("Band table is empty.")
    return bands


def _load_csv(table_path: Path) -> List[Dict[str, str]]:
    if not table_path.exists():
        raise ModuleMainEffectError(f"Missing table: {table_path}")
    with table_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ModuleMainEffectError(f"Missing headers in table {table_path}")
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]


__all__ = [
    "ModuleMainEffectError",
    "module_main_effect_multiplier",
]
