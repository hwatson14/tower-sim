"""
Enemy wave-damage library (wave damage only, enemy types deferred).

Source (canonical runtime tables):
- `tables/inputs/combat/enemy_damage_table.csv`
- `tables/inputs/combat/enemy_health_table.csv`
These tables store per-tier/per-league anchor values keyed by `wave_actual`.

Important:
- Enemy HP/Damage runtime values use log-linear interpolation (linear in ln(value)) between anchor waves.
- For waves below the minimum anchor: fail-closed (raise).
- For waves above the maximum anchor: clamp to the max-anchor value.

Numeric suffixes:
K=1e3, M=1e6, B=1e9, T=1e12, q=1e15, Q=1e18, s=1e21, S=1e24, O=1e27.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv
import math
import re
from bisect import bisect_right
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

from tower_sim.loaders.table_paths import resolve_table_path

_ENEMY_DAMAGE_TABLE_CSV = resolve_table_path("enemy_damage_table")
_ENEMY_HEALTH_TABLE_CSV = resolve_table_path("enemy_health_table")


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
        raise FileNotFoundError(f"Missing enemy scaling table: {path}")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def _load_enemy_scaling_wide_table(path: Path) -> Dict[str, Dict[int, float]]:
    rows = _read_csv_rows(path)
    if not rows:
        raise ValueError(f"Enemy scaling table is empty: {path}")
    headers = list(rows[0].keys())
    if "wave_actual" not in headers:
        raise ValueError(f"Enemy scaling table missing column ['wave_actual']: {path}")

    series_columns = [h for h in headers if h != "wave_actual"]
    if not series_columns:
        raise ValueError(f"Enemy scaling table missing tier/league columns: {path}")

    tables: Dict[str, Dict[int, float]] = {}
    for row in rows:
        wave = int(float(row["wave_actual"]))
        for series in series_columns:
            raw = row.get(series)
            if raw is None or str(raw).strip() == "":
                continue
            value = float(raw)
            if not math.isfinite(value) or value <= 0.0:
                # Canonical tables include overflow tail rows (`inf`) at very high waves.
                # Skip non-finite/non-positive anchors; interpolation/clamping uses finite coverage.
                continue
            tables.setdefault(series.strip(), {})[wave] = value

    if not tables:
        raise ValueError(f"Enemy scaling table had no usable rows: {path}")
    for series, anchors in tables.items():
        if not anchors:
            raise ValueError(f"Enemy scaling series has no finite positive anchors: {series} ({path})")
    return tables


def load_enemy_damage_tables(path: Path = _ENEMY_DAMAGE_TABLE_CSV) -> Dict[str, Dict[int, float]]:
    """Load canonical enemy damage anchor table from `tables/inputs/combat/enemy_damage_table.csv`."""
    return _load_enemy_scaling_wide_table(path)


def load_enemy_health_tables(path: Path = _ENEMY_HEALTH_TABLE_CSV) -> Dict[str, Dict[int, float]]:
    """Load canonical enemy health anchor table from `tables/inputs/combat/enemy_health_table.csv`."""
    return _load_enemy_scaling_wide_table(path)


def load_tier_wave_damage_tables(path: Path = _ENEMY_DAMAGE_TABLE_CSV) -> Dict[str, Dict[int, float]]:
    """Backward-compatible alias for canonical enemy damage table loading."""
    return load_enemy_damage_tables(path)


def load_tier_wave_health_tables(path: Path = _ENEMY_HEALTH_TABLE_CSV) -> Dict[str, Dict[int, float]]:
    """Backward-compatible alias for canonical enemy health table loading."""
    return load_enemy_health_tables(path)


def _log_linear_interpolate(wave: int, lo_wave: int, lo_value: float, hi_wave: int, hi_value: float) -> float:
    if lo_wave >= hi_wave:
        raise ValueError(f"Invalid anchor wave order: lo={lo_wave}, hi={hi_wave}")
    if not math.isfinite(lo_value) or not math.isfinite(hi_value):
        raise ValueError(
            f"Log-linear interpolation requires finite anchor values: lo={lo_value}, hi={hi_value}"
        )
    if lo_value <= 0.0 or hi_value <= 0.0:
        raise ValueError(
            f"Log-linear interpolation requires positive anchor values: lo={lo_value}, hi={hi_value}"
        )

    if wave == lo_wave:
        return lo_value
    if wave == hi_wave:
        return hi_value

    t = (wave - lo_wave) / (hi_wave - lo_wave)
    log_value = math.log(lo_value) + (math.log(hi_value) - math.log(lo_value)) * t
    value = math.exp(log_value)
    if not math.isfinite(value):
        raise ValueError(f"Interpolated non-finite value at wave={wave}: {value}")

    if lo_wave < wave < hi_wave:
        lo_bound = min(lo_value, hi_value)
        hi_bound = max(lo_value, hi_value)
        eps = 1e-12
        if not (lo_bound - eps <= value <= hi_bound + eps):
            raise ValueError(
                "Interpolated value is outside anchor bounds "
                f"at wave={wave}: value={value}, lo={lo_value}, hi={hi_value}"
            )
    return value


def interpolate_anchor_series(anchors: Mapping[int, float], wave: int) -> float:
    """Piecewise log-linear interpolation with explicit edge rules.

    Contract for enemy HP/Damage scaling:
    - Interpolate linearly in ln(value)-space between surrounding anchors.
    - For wave < min_anchor: raise KeyError (fail-closed).
    - For wave > max_anchor: clamp to max anchor value.
    """
    if not anchors:
        raise ValueError("Cannot interpolate empty anchor series")
    wave_i = int(wave)
    anchor_waves = sorted(int(w) for w in anchors.keys())

    min_wave = anchor_waves[0]
    max_wave = anchor_waves[-1]
    if wave_i < min_wave:
        raise KeyError(f"Wave {wave_i} below min anchor {min_wave}")
    if wave_i > max_wave:
        return float(anchors[max_wave])

    if wave_i in anchors:
        return float(anchors[wave_i])

    right = bisect_right(anchor_waves, wave_i)
    lo_wave = anchor_waves[right - 1]
    hi_wave = anchor_waves[right]
    return _log_linear_interpolate(
        wave_i,
        lo_wave,
        float(anchors[lo_wave]),
        hi_wave,
        float(anchors[hi_wave]),
    )

@dataclass(frozen=True)
class EnemyWaveDamageLib:
    """Enemy damage lookup sourced from canonical `enemy_damage_table.csv`."""

    tables: Mapping[str, Mapping[int, float]]

    @staticmethod
    def from_pasted_default() -> "EnemyWaveDamageLib":
        return EnemyWaveDamageLib(parse_pasted_wave_tables(_DEFAULT_PASTED_TABLES))

    @staticmethod
    def from_repo_tables() -> "EnemyWaveDamageLib":
        return EnemyWaveDamageLib(load_enemy_damage_tables())

    def available_tiers(self):
        return sorted(self.tables.keys())

    def wave_damage_exact(self, tier: str, wave: int) -> float:
        """Return enemy damage anchor value for exact (tier/league, wave)."""
        if tier not in self.tables:
            raise KeyError(f"Tier/league {tier!r} not found. Available: {self.available_tiers()}")
        t = self.tables[tier]
        if wave not in t:
            waves = sorted(t.keys())
            lo = max([w for w in waves if w < wave], default=None)
            hi = min([w for w in waves if w > wave], default=None)
            raise KeyError(
                f"Wave {wave} not present for tier/league {tier!r}. "
                f"Nearest anchors: lo={lo}, hi={hi}."
            )
        return float(t[wave])

    def wave_damage(self, tier: str, wave: int) -> float:
        """Return enemy damage at any wave using piecewise log-linear interpolation."""
        if tier not in self.tables:
            raise KeyError(f"Tier/league {tier!r} not found. Available: {self.available_tiers()}")
        return interpolate_anchor_series(self.tables[tier], int(wave))

    def to_dict(self) -> Dict[str, Dict[int, float]]:
        return {k: dict(v) for k, v in self.tables.items()}


@dataclass(frozen=True)
class EnemyWaveHealthLib:
    """Enemy health lookup sourced from canonical `enemy_health_table.csv`."""

    tables: Mapping[str, Mapping[int, float]]

    @staticmethod
    def from_repo_tables() -> "EnemyWaveHealthLib":
        return EnemyWaveHealthLib(load_enemy_health_tables())

    def available_tiers(self):
        return sorted(self.tables.keys())

    def wave_health(self, tier: str, wave: int) -> float:
        """Return enemy health at any wave using piecewise log-linear interpolation."""
        if tier not in self.tables:
            raise KeyError(f"Tier/league {tier!r} not found. Available: {self.available_tiers()}")
        return interpolate_anchor_series(self.tables[tier], int(wave))
