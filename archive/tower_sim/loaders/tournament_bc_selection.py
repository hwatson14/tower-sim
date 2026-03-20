"""Tournament battle-condition (BC) set enumeration for v2 tournament tables.

Scope is intentionally limited to Champion + Legend leagues.
Public BC identity is bc_id = "{bc_key}:{bc_variant}".
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from tower_sim.loaders.table_paths import resolve_table_path
import csv
from typing import Iterable, List, Mapping, Set, Tuple

_DEFAULT_RULES_PATH = resolve_table_path("tournament_league_rules")
_DEFAULT_REGISTRY_PATH = resolve_table_path("heat_bc_registry")


@dataclass(frozen=True)
class LeagueRule:
    league: str
    random_bc_count: int
    has_dd_or_es: bool
    has_more_bosses: bool = True


def _require(condition: bool, msg: str) -> None:
    if not condition:
        raise ValueError(msg)


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _make_bc_id(bc_key: str, bc_variant: str) -> str:
    return f"{bc_key}:{bc_variant}"


def load_bc_registry_keys(path: Path = _DEFAULT_REGISTRY_PATH, *, league: str) -> Set[str]:
    league_key = league.strip().lower()
    if league_key not in {"champion", "legend"}:
        raise ValueError(f"Unknown or unsupported league: {league!r}")
    if not path.exists():
        raise FileNotFoundError(f"Tournament BC registry missing: {path}")

    keys: Set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"bc_key", "bc_variant", "value_unit", "value_kind", "applies_champion", "applies_legend"}
        if reader.fieldnames is None or set(reader.fieldnames) != required:
            raise ValueError(f"Unexpected tournament BC registry header: {reader.fieldnames!r}")
        for row in reader:
            applies = _parse_bool(row[f"applies_{league_key}"])
            if applies:
                keys.add(_make_bc_id(row["bc_key"].strip(), row["bc_variant"].strip()))
    if not keys:
        raise ValueError(f"Tournament BC registry is empty for {league_key}: {path}")
    return keys


def load_league_rules(path: Path = _DEFAULT_RULES_PATH) -> dict[str, LeagueRule]:
    if not path.exists():
        raise FileNotFoundError(f"League rules table missing: {path}")

    with path.open("r", encoding="utf-8") as handle:
        rows = [line for line in handle if line.strip() and not line.lstrip().startswith("#")]
    reader = csv.DictReader(rows)
    required = {"league", "random_bc_count", "has_dd_or_es", "has_more_bosses"}
    if reader.fieldnames is None or set(reader.fieldnames) != required:
        raise ValueError(f"Unexpected league rules header: {reader.fieldnames!r}")

    rules: dict[str, LeagueRule] = {}
    for row in reader:
        league = row["league"].strip().lower()
        rule = LeagueRule(
            league=league,
            random_bc_count=int(row["random_bc_count"]),
            has_dd_or_es=_parse_bool(row["has_dd_or_es"]),
            has_more_bosses=_parse_bool(row["has_more_bosses"]),
        )
        rules[league] = rule

    allowed = {"champion", "legend"}
    if set(rules) != allowed:
        raise ValueError(f"League rules must contain exactly {sorted(allowed)}; got {sorted(rules)}")
    return rules


DEFAULT_LEAGUE_RULES = load_league_rules()


def enumerate_tournament_bc_sets(
    league: str,
    available_bc_ids: Iterable[str] | None = None,
    random_pool_bc_ids: Iterable[str] | None = None,
    league_rules: Mapping[str, LeagueRule] | None = None,
) -> List[Tuple[str, ...]]:
    league_key = league.strip().lower()
    rules = league_rules or DEFAULT_LEAGUE_RULES
    _require(league_key in rules, f"Unknown or unsupported league: {league!r}")
    rule = rules[league_key]

    available: Set[str] = set(
        load_bc_registry_keys(league=league_key) if available_bc_ids is None else {str(x) for x in available_bc_ids}
    )

    fixed: List[str] = []
    more_bosses = "more_bosses:"
    dd_id = "death_defy_down:"
    es_id = "energy_shields_down:"

    if rule.has_more_bosses:
        _require(more_bosses in available, "Missing required bc_id: more_bosses:")
        fixed.append(more_bosses)

    dd_es_choices: List[Tuple[str, ...]] = [tuple()]
    if rule.has_dd_or_es:
        _require(dd_id in available and es_id in available, "Missing required bc_ids for dd/es choice")
        dd_es_choices = [(dd_id,), (es_id,)]

    if random_pool_bc_ids is None:
        pool = available - {more_bosses, dd_id, es_id}
    else:
        pool = {str(x) for x in random_pool_bc_ids}

    _require(
        len(pool) >= rule.random_bc_count,
        f"Random BC pool too small for {league_key}: need {rule.random_bc_count}, have {len(pool)}",
    )

    out: List[Tuple[str, ...]] = []
    for dd_es in dd_es_choices:
        for combo in combinations(sorted(pool), rule.random_bc_count):
            out.append(tuple(sorted(tuple(fixed) + tuple(dd_es) + tuple(combo))))
    return sorted(set(out))
