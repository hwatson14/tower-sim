"""Wiki ingestion for *all* Lab tables.

Design intent
-------------
The simulator should not depend on live network calls.
Instead we keep a cached copy of each lab's (Level, Value, Cost, Total Cost)
table in ``tables/wiki_cache``.

This script refreshes that cache from the primary source:
The Tower - Idle Tower Defense Wiki (Fandom).

Discovery strategy
------------------
1) Parse the ``Lab_Upgrades`` page and collect all links that look like lab
   pages (same-wiki links, excluding sections and non-lab pages).
2) For each discovered lab page, extract the main level table with pandas
   ``read_html``.
3) Write a normalized CSV file: ``lab_<slug>.csv``.

This is deliberately conservative: if we fail to uniquely identify a single
table, we store the page in a "needs manual review" list instead of guessing.

References:
- Lab Upgrades page describes the lab system and lists research items.
  https://the-tower-idle-tower-defense.fandom.com/wiki/Lab_Upgrades
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup


WIKI_BASE = "https://the-tower-idle-tower-defense.fandom.com"
LAB_UPGRADES_URL = f"{WIKI_BASE}/wiki/Lab_Upgrades"


def slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


@dataclass(frozen=True)
class LabPage:
    title: str
    url: str


def _get(url: str, timeout: int = 30) -> str:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def discover_lab_pages() -> list[LabPage]:
    """Return a de-duplicated list of lab pages.

    We discover labs by scanning Lab_Upgrades for internal links.
    """
    html = _get(LAB_UPGRADES_URL)
    soup = BeautifulSoup(html, "html.parser")

    labs: dict[str, LabPage] = {}
    for a in soup.select("a"):
        href = a.get("href") or ""
        text = (a.get_text() or "").strip()
        if not href.startswith("/wiki/"):
            continue
        if ":" in href:  # ignore File:, Category:, etc
            continue
        if href.startswith("/wiki/Lab_Category/"):
            continue
        if href.startswith("/wiki/Milestones"):
            continue
        if "#" in href:
            href = href.split("#", 1)[0]
        if href in ("/wiki/Lab_Upgrades", "/wiki/Labs"):
            continue

        # Heuristic: lab pages are generally simple noun phrases (e.g., "Health")
        # and appear in the Lab_Upgrades list.
        if not text:
            continue
        url = f"{WIKI_BASE}{href}"
        labs[href] = LabPage(title=text, url=url)

    # Stable order by title
    return sorted(labs.values(), key=lambda x: x.title.lower())


def extract_level_table(html: str) -> pd.DataFrame | None:
    """Extract the primary (Level, Value, Cost, Total Cost) table.

    Returns None if we can't confidently find a single correct table.
    """
    # pandas read_html finds all tables; we then filter for the one we want.
    tables = pd.read_html(html)
    candidates: list[pd.DataFrame] = []
    for t in tables:
        cols = [str(c).strip().lower() for c in t.columns]
        if "level" in cols and "value" in cols:
            candidates.append(t)
    if len(candidates) != 1:
        return None
    df = candidates[0].copy()
    # Normalize column names
    df.columns = [str(c).strip().title() for c in df.columns]
    # Keep expected columns if present
    keep = [c for c in ["Level", "Value", "Cost", "Total Cost"] if c in df.columns]
    df = df[keep]
    return df


def write_cache(lab_title: str, df: pd.DataFrame, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(lab_title)
    out = cache_dir / f"lab_{slug}.csv"
    df.to_csv(out, index=False)
    return out


def ingest_all(cache_dir: Path) -> tuple[list[Path], list[LabPage]]:
    """Ingest all labs to cache_dir.

    Returns:
      (written_files, needs_review_pages)
    """
    written: list[Path] = []
    needs_review: list[LabPage] = []

    for lab in discover_lab_pages():
        try:
            html = _get(lab.url)
            df = extract_level_table(html)
            if df is None:
                needs_review.append(lab)
                continue
            written.append(write_cache(lab.title, df, cache_dir))
        except Exception:
            needs_review.append(lab)
    return written, needs_review


def main() -> None:
    cache_dir = Path(__file__).resolve().parents[3] / "tables" / "wiki_cache"
    written, needs_review = ingest_all(cache_dir)
    print(f"Wrote {len(written)} lab tables to {cache_dir}")
    if needs_review:
        print("\nNeeds manual review (table ambiguity or fetch failure):")
        for lab in needs_review:
            print(f"- {lab.title}: {lab.url}")


if __name__ == "__main__":
    main()
