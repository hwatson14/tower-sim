#!/usr/bin/env python3
"""
Tower wiki -> ALL labs (all Lab Category/* pages) -> consolidated per-level tables.

Key changes vs the old approach:
- DO NOT anchor on "Lab Upgrades".
- Enumerate all "Lab Category/*" pages via MediaWiki API (allpages prefix).
- From each category page, extract linked lab page titles.
- For each lab page, extract a per-level table (Level + any of Time/Cost/Value).
- Fail-closed with actionable diagnostics.

Output:
  data/wiki/extracts/labs_compact.json
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

WIKI_API = "https://the-tower-idle-tower-defense.fandom.com/api.php"
OUT_PATH = "data/wiki/extracts/labs_compact.json"

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "TowerSimWikiIngest/2.0 (labs extractor; contact: none)",
    }
)

# -----------------------------
# Helpers
# -----------------------------

def api_get(params: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    r = SESSION.get(WIKI_API, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"Wiki API error: {data['error']}")
    return data


def api_parse_html(page: str) -> str:
    data = api_get(
        {
            "action": "parse",
            "page": page,
            "prop": "text",
            "format": "json",
        }
    )
    # MediaWiki parse returns HTML at ["parse"]["text"]["*"]
    return data["parse"]["text"]["*"]


def normalize_header(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("lv.", "level").replace("lv", "level")
    return s


def is_numeric_level(s: str) -> bool:
    s = s.strip()
    return bool(re.fullmatch(r"\d+", s))


_TIME_RE = re.compile(r"^\s*(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*(?:(\d+)\s*s)?\s*$", re.I)

def parse_time_to_seconds(s: str) -> Optional[int]:
    """
    Parses common wiki time strings like '1h 20m', '45m', '30s', '2d 3h'.
    Returns seconds or None if not parseable/empty.
    """
    s = s.strip()
    if not s:
        return None
    m = _TIME_RE.match(s)
    if not m:
        return None
    d = int(m.group(1) or 0)
    h = int(m.group(2) or 0)
    mi = int(m.group(3) or 0)
    sec = int(m.group(4) or 0)
    return d * 86400 + h * 3600 + mi * 60 + sec


def parse_int_loose(s: str) -> Optional[int]:
    s = s.strip().replace(",", "")
    if not s:
        return None
    # remove common suffixes or decorations
    s = re.sub(r"[^\d]", "", s)
    if not s:
        return None
    return int(s)


def decode_wiki_title_from_href(href: str) -> Optional[str]:
    """
    Convert /wiki/Foo_Bar -> Foo Bar title.
    Ignores non-/wiki/ links.
    """
    if not href.startswith("/wiki/"):
        return None
    title = href[len("/wiki/") :]
    title = title.split("#", 1)[0]
    title = title.split("?", 1)[0]
    title = unquote(title)
    title = title.replace("_", " ")
    return title.strip()


def is_disallowed_namespace(title: str) -> bool:
    # MediaWiki pseudo-namespaces use colon
    return ":" in title


# -----------------------------
# Lab Category discovery
# -----------------------------

def list_lab_category_pages() -> List[str]:
    """
    Enumerate all pages whose title starts with 'Lab Category/' via allpages.
    """
    pages: List[str] = []
    apcontinue: Optional[str] = None
    while True:
        params: Dict[str, Any] = {
            "action": "query",
            "list": "allpages",
            "apprefix": "Lab Category/",
            "apnamespace": 0,
            "aplimit": "max",
            "format": "json",
        }
        if apcontinue:
            params["apcontinue"] = apcontinue

        data = api_get(params)
        batch = data["query"]["allpages"]
        for p in batch:
            pages.append(p["title"])

        cont = data.get("continue", {})
        apcontinue = cont.get("apcontinue")
        if not apcontinue:
            break

    # Deterministic order
    pages = sorted(set(pages))
    return pages


def extract_lab_titles_from_category_page(category_title: str, html: str) -> List[str]:
    """
    Extract lab page titles linked from within the main content of a Lab Category page.
    """
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find("div", class_="mw-parser-output")
    if content is None:
        raise RuntimeError(f"[{category_title}] no mw-parser-output found")

    lab_titles: List[str] = []
    for a in content.find_all("a", href=True):
        t = decode_wiki_title_from_href(a["href"])
        if not t:
            continue
        if t.startswith("Lab Category/"):
            continue
        if is_disallowed_namespace(t):
            continue
        # avoid obvious non-lab hub pages accidentally linked
        if t in ("Labs", "Cards", "Modules", "Perks", "Bots", "Relics", "The Vault"):
            continue
        lab_titles.append(t)

    # de-dupe preserving order
    seen = set()
    out = []
    for t in lab_titles:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


# -----------------------------
# Per-level table extraction
# -----------------------------

@dataclass
class TableParseResult:
    level: List[int]
    time_seconds: List[Optional[int]]
    cost: List[Optional[int]]
    value_raw: List[Optional[str]]
    headers: List[str]


def try_parse_lab_table(table) -> Optional[TableParseResult]:
    """
    Identify and parse a single per-level table.
    Accept if:
      - there is a 'level' column (or first column is numeric levels)
      - and at least one of time/cost/value/effect columns exists
    """
    rows = table.find_all("tr")
    if not rows:
        return None

    # Extract header cells (th) from first row; fallback to first row td if no th.
    header_cells = rows[0].find_all(["th", "td"])
    headers = [normalize_header(c.get_text(" ", strip=True)) for c in header_cells]
    if not headers:
        return None

    # Map columns
    col_level = None
    col_time = None
    col_cost = None
    col_value = None

    for idx, h in enumerate(headers):
        if col_level is None and ("level" in h or h == "#"):
            col_level = idx
        if col_time is None and ("time" in h or "lab time" in h or "duration" in h):
            col_time = idx
        if col_cost is None and ("cost" in h or "coin" in h or "coins" in h):
            col_cost = idx
        if col_value is None and ("value" in h or "effect" in h or "bonus" in h or "multiplier" in h):
            col_value = idx

    # If no explicit level header, allow first column if it looks numeric in body
    if col_level is None:
        col_level = 0

    level: List[int] = []
    time_seconds: List[Optional[int]] = []
    cost: List[Optional[int]] = []
    value_raw: List[Optional[str]] = []

    any_payload_cols = any(c is not None for c in [col_time, col_cost, col_value])
    if not any_payload_cols:
        return None

    for r in rows[1:]:
        cells = r.find_all(["td", "th"])
        if not cells:
            continue
        if col_level >= len(cells):
            continue
        lv_text = cells[col_level].get_text(" ", strip=True)
        if not is_numeric_level(lv_text):
            # tolerate footers/notes
            continue
        lv = int(lv_text)

        def get_cell_text(ci: Optional[int]) -> Optional[str]:
            if ci is None or ci >= len(cells):
                return None
            txt = cells[ci].get_text(" ", strip=True)
            return txt if txt else None

        t_txt = get_cell_text(col_time)
        c_txt = get_cell_text(col_cost)
        v_txt = get_cell_text(col_value)

        level.append(lv)
        time_seconds.append(parse_time_to_seconds(t_txt) if t_txt else None)
        cost.append(parse_int_loose(c_txt) if c_txt else None)
        value_raw.append(v_txt)

    # Require at least 1 parsed level
    if not level:
        return None

    return TableParseResult(
        level=level,
        time_seconds=time_seconds,
        cost=cost,
        value_raw=value_raw,
        headers=headers,
    )


def extract_best_lab_table(lab_title: str, html: str) -> TableParseResult:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find("div", class_="mw-parser-output")
    if content is None:
        raise RuntimeError(f"[{lab_title}] no mw-parser-output found")

    tables = content.find_all("table")
    candidates: List[TableParseResult] = []
    for t in tables:
        res = try_parse_lab_table(t)
        if res:
            candidates.append(res)

    if not candidates:
        # Diagnostics: show first couple table headers if any exist
        diag_headers: List[List[str]] = []
        for t in tables[:3]:
            rows = t.find_all("tr")
            if not rows:
                continue
            header_cells = rows[0].find_all(["th", "td"])
            hs = [normalize_header(c.get_text(" ", strip=True)) for c in header_cells]
            if hs:
                diag_headers.append(hs)
        snippet = content.get_text(" ", strip=True)[:500]
        raise RuntimeError(
            f"[{lab_title}] no relevant per-level table found. "
            f"candidate_headers={diag_headers} content_snippet={snippet!r}"
        )

    # Prefer the table with the most levels (max rows)
    candidates.sort(key=lambda x: len(x.level), reverse=True)
    return candidates[0]


# -----------------------------
# Main
# -----------------------------

def main() -> int:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    print("[wiki] enumerating Lab Category pages via allpages(apprefix=Lab Category/)")
    category_pages = list_lab_category_pages()
    if not category_pages:
        raise RuntimeError("No Lab Category/* pages discovered; wiki structure may have changed.")

    print(f"[wiki] found category_pages={len(category_pages)}")

    category_to_labs: Dict[str, List[str]] = {}
    all_labs: Dict[str, Dict[str, Any]] = {}
    failures: List[str] = []

    for cat in category_pages:
        print(f"[cat] parse {cat}")
        cat_html = api_parse_html(cat)
        lab_titles = extract_lab_titles_from_category_page(cat, cat_html)
        category_to_labs[cat] = lab_titles
        print(f"[cat] {cat} -> labs={len(lab_titles)}")

    # Consolidate unique lab titles
    unique_labs: List[Tuple[str, str]] = []  # (lab_title, category_title)
    seen = set()
    for cat, labs in category_to_labs.items():
        for lab in labs:
            if lab not in seen:
                seen.add(lab)
                unique_labs.append((lab, cat))

    print(f"[wiki] unique_labs={len(unique_labs)}")

    for (lab, cat) in unique_labs:
        print(f"[lab] {lab} (from {cat})")
        try:
            lab_html = api_parse_html(lab)
            table = extract_best_lab_table(lab, lab_html)
            all_labs[lab] = {
                "category": cat,
                "headers": table.headers,
                "level": table.level,
                "time_seconds": table.time_seconds,
                "cost": table.cost,
                "value_raw": table.value_raw,
            }
        except Exception as e:
            failures.append(f"{lab}: {e}")
            print(f"[FAIL] {lab}: {e}", file=sys.stderr)

    if failures:
        print("\n[FAILURES] Some labs could not be parsed. Failing closed.", file=sys.stderr)
        for f in failures[:50]:
            print(f" - {f}", file=sys.stderr)
        if len(failures) > 50:
            print(f" ... and {len(failures)-50} more", file=sys.stderr)
        return 2

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "the-tower-idle-tower-defense.fandom.com (MediaWiki API parse + allpages)",
        "category_pages": category_pages,
        "category_to_labs": category_to_labs,
        "labs": all_labs,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)

    print(f"[ok] wrote {OUT_PATH} (labs={len(all_labs)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
