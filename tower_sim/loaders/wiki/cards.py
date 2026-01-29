from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import pandas as pd

_CACHE_DIR = Path(__file__).resolve().parents[3] / "tables" / "wiki_cache"


@dataclass(frozen=True)
class CardEffect:
    card: str
    rarity: str
    level: int
    value: float
    value_raw: str
    unit: str  # 'mult', 'percent', 'flat', 'seconds', 'unknown'


def _normalise_level_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise cached column names (wiki tables use 'Lv. 1'..'Lv. 7')."""
    rename = {}
    for c in df.columns:
        m = re.match(r"^Lv\.?\s*(\d+)$", str(c).strip())
        if m:
            rename[c] = f"Level {int(m.group(1))}"
    if rename:
        df = df.rename(columns=rename)
    return df


def _load_cards_df() -> pd.DataFrame:
    dfs = []
    for rarity, fname in [("Common", "cards_common.csv"), ("Rare", "cards_rare.csv"), ("Epic", "cards_epic.csv")]:
        p = _CACHE_DIR / fname
        df = pd.read_csv(p)
        df["Rarity"] = rarity
        df = _normalise_level_columns(df)
        dfs.append(df)
    all_df = pd.concat(dfs, ignore_index=True)
    all_df.columns = [str(c).strip().replace("  ", " ") for c in all_df.columns]
    return all_df


_CARDS_DF: pd.DataFrame | None = None


def _cards_df() -> pd.DataFrame:
    global _CARDS_DF
    if _CARDS_DF is None:
        _CARDS_DF = _load_cards_df()
    return _CARDS_DF


def _infer_unit(value_raw: str, description: str | None = None) -> str:
    s = str(value_raw).strip()
    if s.endswith("%"):
        return "percent"
    s_low = s.lower()
    if s_low.endswith("sec") or s_low.endswith("s"):
        return "seconds"
    if s_low.endswith("min"):
        return "seconds"  # minutes will be converted to seconds
    if "x" in s_low:
        return "mult"
    # Many multipliers are presented as plain numbers with an 'x #' in description.
    if description and "x" in description.lower():
        return "mult"
    return "unknown"


def _parse_value(value_raw: str) -> float:
    """Parse the cached numeric value.

    - % -> fraction
    - 'N sec' / 'Ns' -> seconds float
    - 'N min' -> seconds float
    - 'Nx' -> multiplier
    - plain number -> float
    """
    s = str(value_raw).strip().replace(",", "")
    s_low = s.lower()
    if s_low.endswith("%"):
        return float(s_low[:-1]) / 100.0
    if s_low.endswith("min"):
        return float(s_low[:-3].strip()) * 60.0
    if s_low.endswith("sec"):
        return float(s_low[:-3].strip())
    if s_low.endswith("s"):
        return float(s_low[:-1].strip())
    if s_low.endswith("x"):
        return float(s_low[:-1].strip())
    return float(s_low)


def get_card_effect(card_name: str, level: int) -> CardEffect:
    """Return the *raw* effect value at a given card level.

    Important: This is a numeric/units lookup. It does not apply the effect to a build
    (e.g., it won't compute package-chance-per-wave; that happens elsewhere).
    """
    df = _cards_df()
    rows = df[df["Name"].str.lower() == card_name.strip().lower()]
    if rows.empty:
        raise KeyError(f"Unknown card: {card_name!r}")
    if level < 1 or level > 7:
        raise ValueError("Card level must be 1..7")

    col = f"Level {level}"
    if col not in rows.columns:
        raise KeyError(f"Cache missing column {col}")

    raw = rows.iloc[0][col]
    desc = str(rows.iloc[0].get("Description", ""))
    unit = _infer_unit(raw, desc)
    val = _parse_value(raw)
    return CardEffect(
        card=str(rows.iloc[0]["Name"]),
        rarity=str(rows.iloc[0]["Rarity"]),
        level=level,
        value=val,
        value_raw=str(raw),
        unit=unit,
    )
