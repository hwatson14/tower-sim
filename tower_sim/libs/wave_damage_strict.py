"""
Enemy wave-damage library (wave damage only, enemy types deferred).

Source (default runtime tables):
- `tables/tier_wave_damage.csv`
- `tables/tournament_wave_damage.csv`
These tables are the Step1 data dumps for tier and tournament wave damage.

Important:
- No interpolation is performed (to avoid approximations).
- Missing values raise (strict mode).

Numeric suffixes:
K=1e3, M=1e6, B=1e9, T=1e12, q=1e15, Q=1e18, s=1e21, S=1e24, O=1e27.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv
import re
from typing import Dict, Mapping, Optional

_SUFFIX_MAP = {
    "K": 1e3,
    "M": 1e6,
    "B": 1e9,
    "T": 1e12,
    "q": 1e15,
    "Q": 1e18,
    "s": 1e21,
    "S": 1e24,
    "O": 1e27,
}

_DEFAULT_PASTED_TABLES = r"""Wave	Tier 14
1	882.66M
10	3.90B
20	11.92B
30	26.26B
40	47.45B
50	78.32B
60	117.86B
70	167.19B
80	231.76B
90	310.28B
100	414.49B
150	1.21T
200	2.78T
250	5.40T
300	9.41T
400	24.45T
500	51.78T
750	235.37T
1,000	804.91T
1,250	2.16q
1,500	5.20q
2,000	25.11q
2,500	95.14q
3,000	339.59q
3,500	1.07Q
4,500	9.39Q
5,000	24.91Q
5,500	68.31Q
6,000	175.76Q
6,500	446.74Q
7,000	1.14s
7,500	2.83s
8,000	6.76s
8,500	16.68s
9,000	39.78s
9,500	91.57s
10,000	213.46s

Wave	Legend (27.2.2)
1	1.72B
10	48.90B
20	243.98B
30	675.91B
40	1.41T
50	2.58T
60	4.21T
70	6.37T
80	9.34T
90	13.12T
100	18.28T
150	65.95T
200	169.45T
250	378.53T
300	705.00T
400	2.15q
500	5.24q
750	32.77q
1,000	139.38q
1,250	482.10q
1,500	1.39Q
2,000	9.93Q
2,500	54.45Q
3,000	277.20Q
3,500	1.23s
4,500	21.15s
5,000	77.93s
5,500	295.67s
6,000	1.05S
6,500	3.67S
7,000	12.91S
7,500	43.71S
8,000	143.05S
8,500	482.59S
9,000	1.57O
9,500	4.93O
10,000	15.67O

Wave	Champion (27.2.2)
1	476.90K
10	11.98M
20	56.13M
30	150.27M
40	306.31M
50	551.09M
60	886.25M
70	1.33B
80	1.93B
90	2.68B
100	3.71B
150	12.99B
200	32.70B
250	71.91B
300	132.23B
400	396.14B
500	948.57B
750	5.77T
1,000	24.04T
1,250	81.89T
1,500	232.89T
2,000	1.63q
2,500	8.82q
3,000	44.32q
3,500	194.83q
4,500	3.29Q
5,000	12.03Q
5,500	45.33Q
6,000	159.95Q
6,500	556.39Q
7,000	1.95s
7,500	6.56s
8,000	21.37s
8,500	71.81s
9,000	232.86s
9,500	728.32s
10,000	2.30S

Wave	Tier 15
1	5.30B
10	24.21B
20	76.13B
30	170.76B
40	312.26B
50	520.07B
60	788.06B
70	1.12T
80	1.57T
90	2.11T
100	2.82T
150	8.33T
200	19.39T
250	37.90T
300	66.42T
400	174.18T
500	371.46T
750	1.71q
1,000	5.90q
1,250	15.93q
1,500	38.52q
2,000	187.73q
2,500	715.97q
3,000	2.57Q
3,500	8.12Q
4,500	71.86Q
5,000	191.27Q
5,500	526.03Q
6,000	1.36s
6,500	3.46s
7,000	8.87s
7,500	21.96s
8,000	52.61s
8,500	130.08s
9,000	310.74s
9,500	716.52s
10,000	1.67S

Wave	Tier 13
1	147.11M
10	631.52M
20	1.88B
30	4.07B
40	7.26B
50	11.89B
60	17.78B
70	25.08B
80	34.61B
90	46.15B
100	61.43B
150	176.41B
200	403.26B
250	777.46B
300	1.35T
400	3.47T
500	7.31T
750	32.85T
1,000	111.43T
1,250	297.31T
1,500	711.26T
2,000	3.41q
2,500	12.77q
3,000	44.24q
3,500	142.33q
4,500	1.19Q
5,000	3.22Q
5,500	9.00Q
6,000	22.08Q
6,500	58.59Q
7,000	146.76Q
7,500	367.47Q
8,000	847.09Q
8,500	2.17s
9,000	4.82s
9,500	11.89s
10,000	26.61s"""

_TIER_WAVE_DAMAGE_CSV = Path(__file__).resolve().parents[2] / "tables" / "tier_wave_damage.csv"
_TOURNAMENT_WAVE_DAMAGE_CSV = (
    Path(__file__).resolve().parents[2] / "tables" / "tournament_wave_damage.csv"
)

def parse_compact_number(s: str) -> float:
    s = s.strip().replace(",", "")
    m = re.fullmatch(r"([0-9]*\.?[0-9]+)([A-Za-z]?)", s)
    if not m:
        raise ValueError(f"Unparseable number: {s!r}")
    num = float(m.group(1))
    suf = m.group(2)
    if suf == "":
        return num
    if suf not in _SUFFIX_MAP:
        raise ValueError(f"Unknown suffix {suf!r} in {s!r}")
    return num * _SUFFIX_MAP[suf]

def parse_pasted_wave_tables(txt: str) -> Dict[str, Dict[int, float]]:
    """Parse pasted blocks formatted as repeated sections:
    'Wave<TAB><Section Name>' then rows of '<wave><TAB><damage>'.
    Returns: section_name -> {wave:int -> damage:float}
    """
    lines = [ln.strip() for ln in txt.strip().splitlines()]
    sections: Dict[str, Dict[int, float]] = {}
    current: Optional[str] = None

    for ln in lines:
        if not ln:
            continue
        if ln.lower().startswith("wave\t"):
            current = ln.split("\t", 1)[1].strip()
            sections[current] = {}
            continue
        if current is None:
            continue
        parts = re.split(r"\t+", ln)
        if len(parts) < 2:
            continue
        wave_str, dmg_str = parts[0].strip(), parts[1].strip()
        try:
            wave = int(wave_str.replace(",", ""))
        except ValueError:
            continue
        try:
            dmg = parse_compact_number(dmg_str)
        except ValueError:
            continue
        sections[current][wave] = dmg
    return sections


def _read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing wave damage table: {path}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def load_tier_wave_damage_tables(path: Path = _TIER_WAVE_DAMAGE_CSV) -> Dict[str, Dict[int, float]]:
    rows = _read_csv_rows(path)
    required = {"tier", "wave", "wave_damage"}
    if not rows:
        raise ValueError(f"Tier wave damage table is empty: {path}")
    missing = required - set(rows[0].keys())
    if missing:
        raise ValueError(f"Tier wave damage table missing columns {sorted(missing)}: {path}")

    tables: Dict[str, Dict[int, float]] = {}
    for row in rows:
        tier_raw = str(row["tier"]).strip()
        tier_value = float(tier_raw)
        tier_label = f"Tier {int(tier_value)}" if tier_value.is_integer() else f"Tier {tier_raw}"
        wave = int(float(row["wave"]))
        damage = float(row["wave_damage"])
        tables.setdefault(tier_label, {})[wave] = damage
    return tables


def load_tournament_wave_damage_tables(
    path: Path = _TOURNAMENT_WAVE_DAMAGE_CSV,
) -> Dict[str, Dict[int, float]]:
    rows = _read_csv_rows(path)
    required = {"tournament_league", "wave", "wave_damage"}
    if not rows:
        raise ValueError(f"Tournament wave damage table is empty: {path}")
    missing = required - set(rows[0].keys())
    if missing:
        raise ValueError(
            f"Tournament wave damage table missing columns {sorted(missing)}: {path}"
        )

    tables: Dict[str, Dict[int, float]] = {}
    for row in rows:
        league = str(row["tournament_league"]).strip()
        wave = int(float(row["wave"]))
        damage = float(row["wave_damage"])
        tables.setdefault(league, {})[wave] = damage
    return tables


@dataclass(frozen=True)
class EnemyWaveDamageLib:
    """Strict wave-damage lookup. No interpolation."""
    tables: Mapping[str, Mapping[int, float]]

    @staticmethod
    def from_pasted_default() -> "EnemyWaveDamageLib":
        return EnemyWaveDamageLib(parse_pasted_wave_tables(_DEFAULT_PASTED_TABLES))

    @staticmethod
    def from_repo_tables() -> "EnemyWaveDamageLib":
        tables: Dict[str, Dict[int, float]] = {}
        tables.update(load_tier_wave_damage_tables())
        tables.update(load_tournament_wave_damage_tables())
        return EnemyWaveDamageLib(tables)

    def available_tiers(self):
        return sorted(self.tables.keys())

    def wave_damage_exact(self, tier: str, wave: int) -> float:
        """Return wave damage for exact (tier, wave).
        Raises KeyError if tier or wave is missing.
        """
        if tier not in self.tables:
            raise KeyError(f"Tier {tier!r} not found. Available: {self.available_tiers()}")
        t = self.tables[tier]
        if wave not in t:
            # Provide a helpful message that still enforces strictness.
            waves = sorted(t.keys())
            lo = max([w for w in waves if w < wave], default=None)
            hi = min([w for w in waves if w > wave], default=None)
            raise KeyError(
                f"Wave {wave} not present for tier {tier!r} (strict mode). "
                f"Nearest anchors: lo={lo}, hi={hi}. "
                f"Provide full per-wave table CSV to enable complete lookups."
            )
        return float(t[wave])

    def to_dict(self) -> Dict[str, Dict[int, float]]:
        return {k: dict(v) for k, v in self.tables.items()}
