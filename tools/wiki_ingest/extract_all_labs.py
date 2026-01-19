#!/usr/bin/env python3
"""
Tower wiki -> All Labs (all sections) authoritative per-level tables (Level/Time/Cost/Value)
-> consolidated JSON + strict verification (regen + diff) with compression where possible.

Output:
  data/wiki/extracts/labs_compact.json

Fail-closed:
  - Never invent rows.
  - If a lab list can't be discovered from the index page, hard fail.
  - For each lab, if a per-level table can't be found, mark that lab FAIL and exit non-zero.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

# --- Config ---
WIKI_API = "https://the-tower-idle-tower-defense.fandom.com/api.php"

# IMPORTANT: use canonical title with spaces; let API resolve redirects.
LAB_UPGRADES_PAGE = "Lab Upgrades"

OUT_PATH = "data/wiki/extracts/labs_compact.json"

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "TowerSimWikiIngest/1.1 (labs extractor; contact: none)",
    }
)

# Time parsing: canonicalize "Xd Yh Zm" etc to minutes
TIME_RE = re.compile(
    r"^\s*(?:(?P<d>\d+)\s*d)?\s*(?:(?P<h>\d+)\s*h)?\s*(?:(?P<m>\d+)\s*m)?\s*(?:(?P<s>\d+)\s*s)?\s*$",
    re.IGNORECASE,
)

# Wikitext headings like == Attack Research == etc.
HEADING_RE = re.compile(r"^(?P<eq>={2,6})\s*(?P<title>[^=]+?)\s*(?P=eq)\s*$")
# Internal links [[Page]] or [[Page|Text]]
LINK_RE = re.compile(r"\[\[(?P<target>[^\]|#]+)(?:#[^\]|]+)?(?:\|(?P<label>[^\]]+))?\]\]")


@dataclass(frozen=True)
class TableRow:
    level: int
    time_minutes: Optional[int]
    cost: Optional[int]
    value: Optional[float]
    # original strings for strict round-trip comparators (kept for hashing / audit)
    time_raw: Optional[str]
    cost_raw: Optional[str]
    value_raw: Optional[str]


def die(msg: str) -> None:
    print(f"[FATAL] {msg}", file=sys.stderr)
    raise SystemExit(2)


def _api_get(params: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    r = SESSION.get(WIKI_API, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        die(f"MediaWiki API error: {data['error']}")
    return data


def resolve_title(title: str) -> str:
    """
    Resolve redirects + canonical title via action=query.
    """
    data = _api_get(
        {
            "action": "query",
            "titles": title,
            "redirects": 1,
            "format": "json",
        }
    )
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        die(f"Could not resolve title: {title!r} (no pages returned)")
    # pages is dict keyed by pageid
    page = next(iter(pages.values()))
    if "missing" in page:
        die(f"Wiki page missing: {title!r}")
    canonical = page.get("title")
    if not canonical:
        die(f"Could not read canonical title for: {title!r}")
    return canonical


def api_parse_wikitext(page: str) -> str:
    """
    Get rendered wikitext for stable structural parsing (headings + internal links).
    """
    data = _api_get(
        {
            "action": "parse",
            "page": page,
            "prop": "wikitext",
            "redirects": 1,
            "format": "json",
        }
    )
    parse = data.get("parse")
    if not parse:
        die(f"No 'parse' in API response for page {page!r}")
    wt = parse.get("wikitext", {}).get("*")
    if not wt:
        die(f"No wikitext returned for page {page!r}")
    return wt


def api_parse_html(page: str) -> str:
    """
    Get rendered HTML for table scraping.
    """
    data = _api_get(
        {
            "action": "parse",
            "page": page,
            "prop": "text",
            "redirects": 1,
            "format": "json",
        }
    )
    parse = data.get("parse")
    if not parse:
        die(f"No 'parse' in API response for page {page!r}")
    html = parse.get("text", {}).get("*")
    if not html:
        die(f"No html returned for page {page!r}")
    return html


def parse_duration_minutes(s: str) -> Optional[int]:
    s = (s or "").strip()
    if not s:
        return None
    m = TIME_RE.match(s)
    if not m:
        return None
    d = int(m.group("d") or 0)
    h = int(m.group("h") or 0)
    mi = int(m.group("m") or 0)
    sec = int(m.group("s") or 0)
    return d * 24 * 60 + h * 60 + mi + (1 if sec >= 30 else 0)


def parse_int_like(s: str) -> Optional[int]:
    """
    Parse integers like "1,234", "1234", "1.2k" (if present), else None.
    Conservative: only accept plain ints with separators.
    """
    s = (s or "").strip()
    if not s:
        return None
    s2 = s.replace(",", "")
    if re.fullmatch(r"\d+", s2):
        return int(s2)
    # Optional: handle k/m suffix if wiki uses it (only if unambiguous)
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([kKmM])", s)
    if m:
        num = float(m.group(1))
        suf = m.group(2).lower()
        mult = 1000 if suf == "k" else 1_000_000
        # strict rounding: only accept if exact integer after scaling
        val = num * mult
        if abs(val - round(val)) < 1e-9:
            return int(round(val))
    return None


def parse_float_like(s: str) -> Optional[float]:
    s = (s or "").strip()
    if not s:
        return None
    # remove commas
    s2 = s.replace(",", "")
    # allow percent, but preserve numeric part
    if s2.endswith("%"):
        try:
            return float(s2[:-1])
        except ValueError:
            return None
    try:
        return float(s2)
    except ValueError:
        return None


def table_rows_hash(rows: List[TableRow]) -> str:
    """
    Hash original row data (including raw fields) to detect wiki changes.
    """
    payload = [
        {
            "level": r.level,
            "time_raw": r.time_raw,
            "cost_raw": r.cost_raw,
            "value_raw": r.value_raw,
        }
        for r in rows
    ]
    b = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def discover_labs_from_index(index_title: str) -> Dict[str, List[str]]:
    """
    Parse Lab Upgrades page wikitext into {section -> [lab_page_titles...]}.
    We avoid HTML because it is skin/template fragile.
    """
    wt = api_parse_wikitext(index_title)
    section = None
    out: Dict[str, List[str]] = {}
    for line in wt.splitlines():
        hm = HEADING_RE.match(line.strip())
        if hm:
            section = hm.group("title").strip()
            # initialize section bucket
            out.setdefault(section, [])
            continue

        if not section:
            continue

        # Collect internal links on this line.
        for lm in LINK_RE.finditer(line):
            target = (lm.group("target") or "").strip()
            if not target:
                continue

            # Conservative filters: ignore obvious non-lab links
            if target.lower() in {"lab upgrades", "the tower - idle tower defense wiki"}:
                continue
            if target.startswith("File:") or target.startswith("Category:") or target.startswith("Help:"):
                continue

            # Avoid duplicates while preserving order
            if target not in out[section]:
                out[section].append(target)

    # Drop empty sections
    out = {k: v for k, v in out.items() if v}

    if not out:
        die(f"Discovered zero sections/labs from index page: {index_title!r}")

    # Sanity: total labs count must be > 0
    total = sum(len(v) for v in out.values())
    if total == 0:
        die(f"Discovered zero labs from index page: {index_title!r}")

    return out


def extract_first_relevant_table(html: str) -> Tuple[List[str], List[List[str]]]:
    """
    Find a table that looks like it contains Level/Time/Cost/Value.
    Returns (headers, rows-as-strings). Fail-closed if none found.
    """
    soup = BeautifulSoup(html, "lxml")

    # Most fandom tables are 'wikitable'. We'll scan all tables anyway.
    tables = soup.find_all("table")
    for t in tables:
        # get headers
        ths = t.find_all("th")
        if not ths:
            continue
        headers = [th.get_text(" ", strip=True) for th in t.find_all("th")]
        h_norm = [h.lower() for h in headers]

        # Must have "Level" at least
        if not any("level" == h or h.endswith("level") or "level" in h for h in h_norm):
            continue

        # Prefer those with these columns, but allow partial because some labs might omit value or time etc.
        # We'll still parse row-by-row and allow None for missing columns.
        if not (any("time" in h for h in h_norm) or any("duration" in h for h in h_norm) or any("cost" in h for h in h_norm) or any("value" in h for h in h_norm)):
            continue

        # Extract rows
        rows: List[List[str]] = []
        for tr in t.find_all("tr"):
            tds = tr.find_all(["td", "th"])
            if not tds:
                continue
            cells = [td.get_text(" ", strip=True) for td in tds]
            # Skip header-only rows
            if cells and any(c.lower() == "level" for c in cells):
                continue
            rows.append(cells)

        if rows:
            return headers, rows

    die("No relevant per-level table found in lab page HTML")


def map_columns(headers: List[str]) -> Dict[str, Optional[int]]:
    """
    Return column indices for level/time/cost/value if present.
    """
    idx = {"level": None, "time": None, "cost": None, "value": None}
    for i, h in enumerate(headers):
        hn = h.strip().lower()
        if "level" == hn or hn.endswith("level") or "level" in hn:
            idx["level"] = i
        elif "time" in hn or "duration" in hn:
            idx["time"] = i
        elif "cost" in hn:
            idx["cost"] = i
        elif "value" in hn or "effect" in hn:
            idx["value"] = i
    if idx["level"] is None:
        die(f"Table missing Level column. headers={headers}")
    return idx


def build_rows(headers: List[str], raw_rows: List[List[str]]) -> List[TableRow]:
    col = map_columns(headers)
    out: List[TableRow] = []

    for r in raw_rows:
        # Some tables have fewer cells than headers due to rowspans. Fail-closed (don't guess).
        if len(r) < (max(i for i in col.values() if i is not None) + 1):
            continue  # skip malformed row rather than inventing

        lvl_raw = r[col["level"]] if col["level"] is not None else ""
        lvl = parse_int_like(lvl_raw)
        if lvl is None:
            # If the first column isn't numeric, it's not a data row
            continue

        time_raw = r[col["time"]] if col["time"] is not None else None
        cost_raw = r[col["cost"]] if col["cost"] is not None else None
        value_raw = r[col["value"]] if col["value"] is not None else None

        time_min = parse_duration_minutes(time_raw) if time_raw is not None else None
        cost = parse_int_like(cost_raw) if cost_raw is not None else None
        value = parse_float_like(value_raw) if value_raw is not None else None

        out.append(
            TableRow(
                level=lvl,
                time_minutes=time_min,
                cost=cost,
                value=value,
                time_raw=time_raw,
                cost_raw=cost_raw,
                value_raw=value_raw,
            )
        )

    if not out:
        die("Parsed table but produced zero data rows (no numeric levels found)")
    # Ensure levels are strictly increasing
    out_sorted = sorted(out, key=lambda x: x.level)
    for i in range(1, len(out_sorted)):
        if out_sorted[i].level <= out_sorted[i - 1].level:
            die("Levels not strictly increasing after parse (table malformed)")
    return out_sorted


# ---- Compression models ----

def try_arithmetic(seq: List[Optional[float]]) -> Optional[Dict[str, Any]]:
    """
    Exact arithmetic progression for numeric columns. None values disqualify.
    """
    if any(v is None for v in seq):
        return None
    vals = [float(v) for v in seq]  # safe
    if len(vals) < 2:
        return {"type": "arithmetic", "a0": vals[0], "d": 0.0, "round": "none"}
    d = vals[1] - vals[0]
    for i in range(2, len(vals)):
        if vals[i] != vals[0] + d * i:
            return None
    return {"type": "arithmetic", "a0": vals[0], "d": d, "round": "none"}


def try_geometric(seq: List[Optional[float]]) -> Optional[Dict[str, Any]]:
    """
    Exact geometric progression for numeric columns. None values disqualify.
    Requires non-zero start.
    """
    if any(v is None for v in seq):
        return None
    vals = [float(v) for v in seq]
    if len(vals) < 2:
        return {"type": "geometric", "a0": vals[0], "r": 1.0, "round": "none"}
    if vals[0] == 0:
        return None
    r = vals[1] / vals[0]
    for i in range(2, len(vals)):
        if vals[i] != vals[0] * (r ** i):
            return None
    return {"type": "geometric", "a0": vals[0], "r": r, "round": "none"}


def model_or_lookup(name: str, rows: List[TableRow]) -> Dict[str, Any]:
    """
    For each column, try smallest exact model. Otherwise fallback to lookup.
    We do not pretend we can fit piecewise models without explicit evidence;
    we can add piecewise later if needed.
    """
    levels = [r.level for r in rows]

    def col_seq(getter):
        return [getter(r) for r in rows]

    time_seq = col_seq(lambda r: r.time_minutes)
    cost_seq = col_seq(lambda r: r.cost)
    value_seq = col_seq(lambda r: r.value)

    def fit_numeric(seq: List[Optional[float]]) -> Dict[str, Any]:
        # Try arithmetic then geometric
        m = try_arithmetic(seq)
        if m:
            return m
        m = try_geometric(seq)
        if m:
            return m
        # fallback: lookup
        return {"type": "lookup", "values": seq, "round": "none"}

    model = {
        "levels": {"type": "lookup", "values": levels, "round": "none"},
        "time_minutes": fit_numeric([float(v) if v is not None else None for v in time_seq]),
        "cost": fit_numeric([float(v) if v is not None else None for v in cost_seq]),
        "value": fit_numeric([float(v) if v is not None else None for v in value_seq]),
    }
    return model


def regen_from_model(model: Dict[str, Any], n: int) -> Dict[str, List[Optional[float]]]:
    def regen_col(col: Dict[str, Any]) -> List[Optional[float]]:
        t = col["type"]
        if t == "lookup":
            vals = col["values"]
            if len(vals) != n:
                die("lookup model length mismatch during regen")
            return vals
        if t == "arithmetic":
            a0 = col["a0"]
            d = col["d"]
            return [a0 + d * i for i in range(n)]
        if t == "geometric":
            a0 = col["a0"]
            r = col["r"]
            return [a0 * (r ** i) for i in range(n)]
        die(f"Unknown model type: {t}")

    return {
        "levels": regen_col(model["levels"]),
        "time_minutes": regen_col(model["time_minutes"]),
        "cost": regen_col(model["cost"]),
        "value": regen_col(model["value"]),
    }


def strict_verify(name: str, rows: List[TableRow], model: Dict[str, Any]) -> None:
    """
    Strict equality for numbers (after regen), and time equality on minutes.
    """
    n = len(rows)
    regen = regen_from_model(model, n)

    # levels: strict ints
    for i in range(n):
        if int(regen["levels"][i]) != rows[i].level:
            die(f"[{name}] level mismatch at i={i}: regen={regen['levels'][i]} wiki={rows[i].level}")

    # time minutes strict equality when present
    for i in range(n):
        r = rows[i].time_minutes
        g = regen["time_minutes"][i]
        if r is None and g is None:
            continue
        if r is None or g is None:
            die(f"[{name}] time presence mismatch at level={rows[i].level}: regen={g} wiki={r}")
        if float(r) != float(g):
            die(f"[{name}] time mismatch at level={rows[i].level}: regen={g} wiki={r}")

    # cost strict numeric equality when present
    for i in range(n):
        r = rows[i].cost
        g = regen["cost"][i]
        if r is None and g is None:
            continue
        if r is None or g is None:
            die(f"[{name}] cost presence mismatch at level={rows[i].level}: regen={g} wiki={r}")
        if float(r) != float(g):
            die(f"[{name}] cost mismatch at level={rows[i].level}: regen={g} wiki={r}")

    # value strict numeric equality when present
    for i in range(n):
        r = rows[i].value
        g = regen["value"][i]
        if r is None and g is None:
            continue
        if r is None or g is None:
            die(f"[{name}] value presence mismatch at level={rows[i].level}: regen={g} wiki={r}")
        if float(r) != float(g):
            die(f"[{name}] value mismatch at level={rows[i].level}: regen={g} wiki={r}")


def main() -> int:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    index_title = resolve_title(LAB_UPGRADES_PAGE)
    print(f"[wiki] index canonical title: {index_title}")

    sections = discover_labs_from_index(index_title)
    total = sum(len(v) for v in sections.values())
    print(f"[wiki] discovered sections={len(sections)} labs_total={total}")

    extracted: List[Dict[str, Any]] = []
    failures: List[str] = []

    for section, labs in sections.items():
        for lab_title in labs:
            lab_canonical = resolve_title(lab_title)
            print(f"[lab] {section} :: {lab_canonical}")
            try:
                html = api_parse_html(lab_canonical)
                headers, raw_rows = extract_first_relevant_table(html)
                rows = build_rows(headers, raw_rows)

                model = model_or_lookup(lab_canonical, rows)
                strict_verify(lab_canonical, rows, model)

                extracted.append(
                    {
                        "section": section,
                        "title": lab_canonical,
                        "source": {
                            "wiki": "the-tower-idle-tower-defense.fandom.com",
                            "page": lab_canonical,
                        },
                        "table_hash_sha256": table_rows_hash(rows),
                        "table_headers": headers,
                        "table_rows_raw": [
                            {
                                "level": r.level,
                                "time_raw": r.time_raw,
                                "cost_raw": r.cost_raw,
                                "value_raw": r.value_raw,
                            }
                            for r in rows
                        ],
                        "parsed": {
                            "level": [r.level for r in rows],
                            "time_minutes": [r.time_minutes for r in rows],
                            "cost": [r.cost for r in rows],
                            "value": [r.value for r in rows],
                        },
                        "model": model,
                    }
                )
            except Exception as e:
                failures.append(f"{lab_title} ({section}): {e}")
                print(f"[FAIL] {lab_title} ({section}): {e}", file=sys.stderr)

    if failures:
        print("[FATAL] One or more labs failed extraction; failing closed.", file=sys.stderr)
        for f in failures[:50]:
            print(f"  - {f}", file=sys.stderr)
        return 2

    out_obj = {
        "source_index_page": index_title,
        "sections": sections,
        "labs": extracted,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"[ok] wrote {OUT_PATH} labs={len(extracted)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
