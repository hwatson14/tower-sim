from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, Optional

import pandas as pd


_SUFFIXES = {
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


def parse_compact_number(x: object) -> float:
    """Parse a compact number like '882.66M' or '9.39Q' into a float.

    This is used for Skye-style wave damage tables.

    Rules:
    - supports suffixes: K,M,B,T,q,Q,s,S,O
    - commas in the numeric portion are ignored
    - empty/None -> raises
    """

    if x is None:
        raise ValueError("Cannot parse None")
    s = str(x).strip()
    if s == "":
        raise ValueError("Cannot parse empty string")

    # strip commas
    s = s.replace(",", "")
    suf = s[-1]
    if suf in _SUFFIXES:
        base = float(s[:-1])
        return base * _SUFFIXES[suf]
    # plain numeric
    return float(s)


@dataclass(frozen=True)
class WaveDamageTable:
    """Exact wave damage lookup table.

    For v1 we implement *exact* lookups only. If a wave is missing from the
    table, we raise rather than interpolate.

    Expected CSV columns: Tier, Wave, WaveDamage
    Tier may be numeric (e.g. 14) or strings like 'T14'.
    """

    _by_key: Dict[Tuple[str, int], float]

    @staticmethod
    def from_csv(df: pd.DataFrame) -> "WaveDamageTable":
        required = {"Tier", "Wave", "WaveDamage"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"WaveDamage CSV missing columns: {sorted(missing)}")

        by_key: Dict[Tuple[str, int], float] = {}
        for _, row in df.iterrows():
            tier_raw = str(row["Tier"]).strip()
            tier = tier_raw if tier_raw.upper().startswith("T") else f"T{tier_raw}"
            w = int(row["Wave"])
            dmg = parse_compact_number(row["WaveDamage"])
            by_key[(tier, w)] = float(dmg)

        return WaveDamageTable(_by_key=by_key)

    def wave_damage(self, tier: str, wave: int) -> float:
        key = (tier if tier.upper().startswith("T") else f"T{tier}", int(wave))
        if key not in self._by_key:
            raise KeyError(
                f"WaveDamage missing exact entry for {key}. "
                "Provide a per-wave table or add an interpolation mode explicitly."
            )
        return self._by_key[key]


def validate_monotonic(df: pd.DataFrame, tier_col: str = "Tier", wave_col: str = "Wave", dmg_col: str = "WaveDamage") -> None:
    """Best-effort monotonic check: within each tier, Wave and damage should increase."""
    # We keep this as a validator (warn/raise depending on calling context).
    tmp = df[[tier_col, wave_col, dmg_col]].copy()
    tmp[dmg_col] = tmp[dmg_col].map(parse_compact_number)
    tmp[wave_col] = tmp[wave_col].astype(int)

    for tier, g in tmp.groupby(tier_col):
        g = g.sort_values(wave_col)
        waves = g[wave_col].to_list()
        if waves != sorted(waves):
            raise ValueError(f"WaveDamage table for {tier} has non-monotonic waves")
        dmgs = g[dmg_col].to_list()
        # allow equality (some tables may repeat at low waves), but not decreases
        for i in range(1, len(dmgs)):
            if dmgs[i] < dmgs[i - 1]:
                raise ValueError(f"WaveDamage table for {tier} decreases at row {i}")
