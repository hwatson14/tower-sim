from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from tower_sim.loaders.table_paths import resolve_table_path
from typing import Dict, List, Optional


class UnknownBotError(KeyError):
    pass


class UnknownBotAttributeError(KeyError):
    pass


class InvalidBotLevelError(ValueError):
    pass


@dataclass(frozen=True)
class BotAttributeLevels:
    bot: str
    attribute: str
    values: Dict[int, float]
    costs: Dict[int, Optional[float]]
    max_levels: set[int]


REQUIRED_HEADERS = {
    "bot",
    "attribute",
    "level",
    "value",
    "cost",
    "is_max",
    "source_path",
    "source_sha256",
    "source_modified_utc",
    "source_sheet",
}


def _default_table_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return resolve_table_path("bot_upgrades")


def _parse_level(value: str) -> int:
    candidate = value.strip()
    if candidate == "":
        raise ValueError("Missing level value")
    try:
        numeric = float(candidate)
    except ValueError as exc:
        raise ValueError(f"Invalid level value: {value}") from exc
    if not numeric.is_integer():
        raise ValueError(f"Non-integer level value: {value}")
    return int(numeric)


def _parse_value(value: str) -> float:
    candidate = value.strip()
    if candidate == "":
        raise ValueError("Missing value")
    return float(candidate)


def _parse_cost(value: str) -> Optional[float]:
    candidate = value.strip()
    if candidate == "":
        return None
    return float(candidate)


def _parse_is_max(value: str) -> bool:
    candidate = value.strip().lower()
    if candidate not in {"true", "false"}:
        raise ValueError(f"Invalid is_max value: {value}")
    return candidate == "true"


def load_bot_upgrades(path: Path | None = None) -> Dict[str, Dict[str, BotAttributeLevels]]:
    table_path = path or _default_table_path()
    if not table_path.exists():
        raise FileNotFoundError(f"Missing bot upgrades table: {table_path}")

    with table_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Bot upgrades table missing headers")
        missing = REQUIRED_HEADERS.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"Bot upgrades table missing columns: {sorted(missing)}")

        bots: Dict[str, Dict[str, BotAttributeLevels]] = {}
        for row in reader:
            bot = row["bot"].strip()
            attribute = row["attribute"].strip()
            level = _parse_level(row["level"])
            value = _parse_value(row["value"])
            cost = _parse_cost(row["cost"])
            is_max = _parse_is_max(row["is_max"])

            bot_attrs = bots.setdefault(bot, {})
            existing = bot_attrs.get(attribute)
            if existing is None:
                bot_attrs[attribute] = BotAttributeLevels(
                    bot=bot,
                    attribute=attribute,
                    values={level: value},
                    costs={level: cost},
                    max_levels={level} if is_max else set(),
                )
                continue

            if level in existing.values:
                raise ValueError(f"Duplicate level {level} for bot {bot} attribute {attribute}")
            existing.values[level] = value
            existing.costs[level] = cost
            if is_max:
                existing.max_levels.add(level)

    if not bots:
        raise ValueError("Bot upgrades table is empty")

    return bots


@lru_cache(maxsize=1)
def _load_default_bot_upgrades() -> Dict[str, Dict[str, BotAttributeLevels]]:
    return load_bot_upgrades()


def list_bots() -> List[str]:
    return sorted(_load_default_bot_upgrades().keys())


def list_bot_attributes(bot: str) -> List[str]:
    bots = _load_default_bot_upgrades()
    if bot not in bots:
        raise UnknownBotError(f"Unknown bot: {bot!r}")
    return sorted(bots[bot].keys())


def get_bot_attribute(bot: str, attribute: str, level: int) -> tuple[float, Optional[float], bool]:
    bots = _load_default_bot_upgrades()
    if bot not in bots:
        raise UnknownBotError(f"Unknown bot: {bot!r}")
    bot_attrs = bots[bot]
    if attribute not in bot_attrs:
        raise UnknownBotAttributeError(f"Unknown bot attribute: {attribute!r} for bot {bot!r}")
    if level <= 0 and level not in bot_attrs[attribute].values:
        raise InvalidBotLevelError(f"Invalid level {level} for bot {bot!r} attribute {attribute!r}")
    entry = bot_attrs[attribute]
    if level not in entry.values:
        raise InvalidBotLevelError(f"Invalid level {level} for bot {bot!r} attribute {attribute!r}")
    return entry.values[level], entry.costs[level], level in entry.max_levels


def bots_from_table(path: Path | None = None) -> Dict[str, Dict[str, BotAttributeLevels]]:
    return load_bot_upgrades(path)


__all__ = [
    "BotAttributeLevels",
    "InvalidBotLevelError",
    "UnknownBotAttributeError",
    "UnknownBotError",
    "bots_from_table",
    "get_bot_attribute",
    "list_bot_attributes",
    "list_bots",
    "load_bot_upgrades",
]
