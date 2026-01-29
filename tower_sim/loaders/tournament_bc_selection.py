"""Tournament battle-condition (BC) set selection.

Provenance:
- Tournament league rules are sourced from
  reference/step1_dump_docs/part4_legacy_quarantine/quarantine/recovered_data/_recovered_v1.6.54/
  data/tournaments/leagues_and_heat.yaml with wiki evidence recorded in
  reference/step1_dump_docs/part4_legacy_quarantine/quarantine/recovered_data/_recovered_v1.6.34/
  evidence/tournament_heat_wiki_notes.yaml (wiki URL:
  https://the-tower-idle-tower-defense.fandom.com/wiki/Tournaments).

Deterministic rules:
- "More Bosses" is always present when enabled by the league rule.
- Platinum+ forces either "Death Defy Down" or "Energy Shields Down".
- Additional BCs are selected from a random pool, but this module only enumerates
  all possible sets; it does not sample.

Fail-closed rules:
- Unknown league -> error.
- Required BC ids missing -> error.
- Random pool smaller than required -> error.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
import csv
from typing import Iterable, List, Mapping, Sequence, Set, Tuple

_DEFAULT_RULES_PATH = (
    Path(__file__).resolve().parents[2] / "tables" / "tournament_league_rules.csv"
)


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


def load_league_rules(path: Path = _DEFAULT_RULES_PATH) -> dict[str, LeagueRule]:
    """Load league rules from a CSV file with comment support (#)."""
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
    return rules


DEFAULT_LEAGUE_RULES = load_league_rules()


def enumerate_tournament_bc_sets(
    *,
    league: str,
    available_bc_ids: Iterable[str],
    random_pool_bc_ids: Iterable[str] | None = None,
    league_rules: Mapping[str, LeagueRule] | None = None,
) -> List[Tuple[str, ...]]:
    """Enumerate all BC sets possible for a given league.

    Returns a list of sorted tuples of bc_id.
    """

    league_key = league.strip().lower()
    rules = league_rules or DEFAULT_LEAGUE_RULES
    _require(league_key in rules, f"Unknown league: {league!r}")
    rule = rules[league_key]

    available: Set[str] = {str(x) for x in available_bc_ids}

    fixed: List[str] = []
    if rule.has_more_bosses:
        _require("more_bosses" in available, "Missing required bc_id: more_bosses")
        fixed.append("more_bosses")

    dd_es_choices: List[Tuple[str, ...]] = [tuple()]
    if rule.has_dd_or_es:
        _require(
            "death_defy_down" in available and "energy_shields_down" in available,
            "Missing required bc_ids for dd/es choice",
        )
        dd_es_choices = [("death_defy_down",), ("energy_shields_down",)]

    if random_pool_bc_ids is None:
        pool = available - {"more_bosses", "death_defy_down", "energy_shields_down"}
    else:
        pool = {str(x) for x in random_pool_bc_ids}

    _require(
        len(pool) >= rule.random_bc_count,
        (
            "Random BC pool too small for "
            f"{league_key}: need {rule.random_bc_count}, have {len(pool)}"
        ),
    )

    out: List[Tuple[str, ...]] = []
    for dd_es in dd_es_choices:
        for combo in combinations(sorted(pool), rule.random_bc_count):
            bc_set = tuple(sorted(tuple(fixed) + tuple(dd_es) + tuple(combo)))
            out.append(bc_set)

    out = sorted(set(out))
    return out
