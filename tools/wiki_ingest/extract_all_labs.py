#!/usr/bin/env python3
"""
Tower wiki → ALL labs (all sections) → authoritative per-level tables (Level/Time/Cost/Value) → exact compression
→ consolidated JSON → strict verification (regen + diff)

Output:
  data/wiki/extracts/labs_compact.json

Fail-closed:
- Never invents rows.
- If a lab table can't be found/parsed or a model can't exactly reproduce, it falls back to lookup.
- If lookup can't be produced (table missing), that lab is marked FAIL and the script exits non-zero.
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

WIKI_API = "https://the-tower-idle-tower-defense.fandom.com/api.php"
LAB_UPGRADES_PAGE = "Lab_Upgrades"
OUT_PATH = "data/wiki/extracts/labs_compact.json"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "TowerSimWikiIngest/1.0 (labs extractor; contact: none)"})

TIME_RE = re.compile(r"^\s*(?:(\d+)\s*d)?\s*(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?\s*$", re.IGNORECASE)


def api_parse_html(page: str) -> str:
    r = SESSION.get(
        WIKI_API,
        params={"action": "parse", "page": page, "prop": "text", "format": "json"},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"API error for {page}: {data['error']}")
    return data["parse"]["text"]["*"]


def time_to_minutes(s: str) -> int:
    s = s.strip()
    m = TIME_RE.match(s)
    if not m:
        raise ValueError(f"Unparseable time string: {s!r}")
    d = int(m.group(1) or 0)
    h = int(m.group(2) or 0)
    mi = int(m.group(3) or 0)
    return d * 24 * 60 + h * 60 + mi


def normalize_int_commas(s: str) -> int:
    t = s.strip().replace(",", "")
    if not re.fullmatch(r"\d+", t):
        raise ValueError(f"Unparseable integer: {s!r}")
    return int(t)


def normalize_value_numeric(s: str) -> Optional[float]:
    t = s.strip()
    if not t:
        return None
    if t.lower().startswith("x"):
        try:
            return float(t[1:])
        except:
            return None
    if t.endswith("%"):
        try:
            return float(t[:-1])
        except:
            return None
    if re.fullmatch(r"\d+(\.\d+)?", t):
        return float(t)
    return None


def sha256_canonical_rows(rows: List[Dict[str, Any]]) -> str:
    blob = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def find_list_anchor(soup: BeautifulSoup) -> Any:
    # Try common ids used by Fandom render
    for pat in ["List_of_Lab_Upgrades", "List of Lab Upgrades"]:
        el = soup.find(id=re.compile(pat))
        if el:
            return el
    # Fallback: locate an h2/h3 containing the text
    for h in soup.find_all(["h2", "h3"]):
        if "List of Lab Upgrades" in h.get_text(" ", strip=True):
            return h
    raise RuntimeError("Could not locate 'List of Lab Upgrades' section on Lab_Upgrades page")


def extract_all_sections_and_labs() -> Dict[str, List[Tuple[str, str, int]]]:
    """
    Returns:
      section_name -> list of (lab_name, page_title, max_level)

    This is dynamic: it does NOT hardcode sections. It takes every section under
    'List of Lab Upgrades' until the list clearly ends.
    """
    html = api_parse_html(LAB_UPGRADES_PAGE)
    soup = BeautifulSoup(html, "html.parser")
    anchor = find_list_anchor(soup)

    out: Dict[str, List[Tuple[str, str, int]]] = {}
    cur_section: Optional[str] = None

    # Start scanning from the anchor's parent block
    start = anchor.parent if hasattr(anchor, "parent") else anchor

    for el in start.find_all_next(["h2", "h3", "p", "ul", "ol"], limit=4000):
        txt = el.get_text(" ", strip=True)

        # Section headers are h3/h2, often named "Main Research", "Attack Research", etc.
        if el.name in ("h2", "h3"):
            section_name = txt
            # Stop when we hit non-lab upgrade areas (wiki-dependent); conservative stops:
            if section_name in ("Other Upgrades", "Notes", "Trivia", "Gallery", "References"):
                break
            cur_section = section_name
            out.setdefault(cur_section, [])
            continue

        if cur_section is None:
            continue

        if "Max Lv" in txt:
            mmax = re.search(r"Max\s+Lv\s+(\d+)", txt, re.IGNORECASE)
            if not mmax:
                continue
            max_lv = int(mmax.group(1))

            link = el.find("a", href=True)
            if not link:
                continue
            lab_name = link.get_text(" ", strip=True)
            href = link["href"]
            mtitle = re.search(r"/wiki/([^#?]+)", href)
            if not mtitle:
                continue
            page_title = mtitle.group(1)
            out[cur_section].append((lab_name, page_title, max_lv))

    # Fail-closed: must find at least one lab and at least 3 sections (practically all labs)
    total = sum(len(v) for v in out.values())
    if total == 0:
        raise RuntimeError("Extracted zero labs from Lab_Upgrades")
    if len(out) < 3:
        raise RuntimeError(f"Extracted too few sections ({len(out)}). Likely parsing failed.")
    return out


def extract_lab_table(page_title: str) -> List[Dict[str, Any]]:
    """
    Extract first table with Level + Time + Cost columns.
    Returns row dicts with parsed + original.
    """
    html = api_parse_html(page_title)
    soup = BeautifulSoup(html, "html.parser")

    tables = soup.find_all("table")
    for t in tables:
        ths = t.find_all("th")
        if not ths:
            continue
        headers = [th.get_text(" ", strip=True).strip().lower() for th in ths]
        # Normalize common header variants
        def is_time(h: str) -> bool:
            return "time" in h or "duration" in h

        if ("level" in headers) and any(is_time(h) for h in headers) and ("cost" in headers):
            level_i = next(i for i, h in enumerate(headers) if h == "level")
            time_i = next(i for i, h in enumerate(headers) if is_time(h))
            cost_i = next(i for i, h in enumerate(headers) if h == "cost")

            # value column could be "value", "bonus", "effect" etc. If absent, keep empty string.
            value_i = None
            for i, h in enumerate(headers):
                if h in ("value", "bonus", "effect"):
                    value_i = i
                    break

            rows: List[Dict[str, Any]] = []
            for tr in t.find_all("tr"):
                tds = tr.find_all("td")
                if not tds:
                    continue
                cells = [td.get_text(" ", strip=True) for td in tds]
                if max(level_i, time_i, cost_i, value_i or 0) >= len(cells):
                    continue

                lev_s = cells[level_i].replace(",", "").strip()
                if not re.fullmatch(r"\d+", lev_s):
                    continue
                level = int(lev_s)

                time_text = cells[time_i].strip()
                cost_text = cells[cost_i].strip()
                value_text = (cells[value_i].strip() if value_i is not None else "")

                row = {
                    "level": level,
                    "time_text": time_text,
                    "time_min": time_to_minutes(time_text),
                    "cost_text": cost_text,
                    "cost_int": normalize_int_commas(cost_text),
                    "value_text": value_text,
                    "value_num": normalize_value_numeric(value_text),
                }
                rows.append(row)

            if rows:
                rows.sort(key=lambda r: r["level"])
                levels = [r["level"] for r in rows]
                if len(levels) != len(set(levels)):
                    raise RuntimeError(f"Duplicate levels on {page_title}")
                return rows

    raise RuntimeError(f"No Level/Time/Cost lab table found on {page_title}")


@dataclass
class Model:
    kind: str  # arithmetic | geometric | piecewise2 | lookup
    params: Dict[str, Any]
    rounding: Dict[str, Any]


def fit_arithmetic(seq: List[int]) -> Optional[Model]:
    if len(seq) < 2:
        return Model("lookup", {"values": seq}, {"type": "int_exact"})
    d = seq[1] - seq[0]
    if all(seq[i] - seq[i - 1] == d for i in range(2, len(seq))):
        return Model("arithmetic", {"a0": seq[0], "d": d}, {"type": "int_exact"})
    return None


def fit_geometric(seq: List[int]) -> Optional[Model]:
    if len(seq) < 2 or seq[0] == 0:
        return None
    r_num, r_den = seq[1], seq[0]
    for i in range(2, len(seq)):
        if seq[i - 1] == 0:
            return None
        if seq[i] * r_den != seq[i - 1] * r_num:
            return None
    g = math.gcd(r_num, r_den)
    r_num //= g
    r_den //= g
    return Model("geometric", {"a0": seq[0], "r_num": r_num, "r_den": r_den}, {"type": "int_exact"})


def gen_int(model: Model, n: int) -> List[int]:
    if model.kind == "lookup":
        return model.params["values"][:n]
    if model.kind == "arithmetic":
        a0, d = model.params["a0"], model.params["d"]
        return [a0 + i * d for i in range(n)]
    if model.kind == "geometric":
        a0, r_num, r_den = model.params["a0"], model.params["r_num"], model.params["r_den"]
        out = [a0]
        for _ in range(1, n):
            prev = out[-1]
            if (prev * r_num) % r_den != 0:
                raise RuntimeError("Non-integer geometric step")
            out.append((prev * r_num) // r_den)
        return out
    if model.kind == "piecewise2":
        split = model.params["split"]
        left = Model(**model.params["left"])
        right = Model(**model.params["right"])
        return gen_int(left, split) + gen_int(right, n - split)
    raise RuntimeError(f"Unknown model kind {model.kind}")


def fit_piecewise2(seq: List[int]) -> Optional[Model]:
    n = len(seq)
    if n < 6:
        return None
    for split in range(2, n - 2):
        left_seq = seq[:split]
        right_seq = seq[split:]
        for lf in (fit_arithmetic(left_seq), fit_geometric(left_seq)):
            if not lf:
                continue
            for rf in (fit_arithmetic(right_seq), fit_geometric(right_seq)):
                if not rf:
                    continue
                return Model(
                    "piecewise2",
                    {"split": split, "left": lf.__dict__, "right": rf.__dict__},
                    {"type": "int_exact"},
                )
    return None


def fit_best_int(seq: List[int]) -> Model:
    for f in (fit_arithmetic, fit_geometric, fit_piecewise2):
        m = f(seq)
        if m:
            # verify exact match
            if gen_int(m, len(seq)) == seq:
                return m
    return Model("lookup", {"values": seq}, {"type": "int_exact"})


def fit_value_model(value_texts: List[str], value_nums: List[Optional[float]]) -> Model:
    if not value_texts:
        return Model("lookup", {"values": []}, {"type": "text"})

    all_numeric = all(v is not None for v in value_nums)
    if not all_numeric:
        return Model("lookup", {"values": value_texts}, {"type": "text"})

    nums = [v for v in value_nums if v is not None]  # type: ignore
    # exact scaling to ints (try smallest scale)
    for scale in (1, 10, 100, 1000):
        ints = []
        ok = True
        for v in nums:
            x = v * scale
            if abs(x - round(x)) > 1e-9:
                ok = False
                break
            ints.append(int(round(x)))
        if ok:
            m = fit_best_int(ints)
            m.rounding = {"type": "scaled_int_exact", "scale": scale}
            return m

    # fallback: keep exact strings
    return Model("lookup", {"values": value_texts}, {"type": "text"})


def regen_value(model: Model, n: int) -> Tuple[List[str], List[Optional[float]]]:
    if model.rounding.get("type") == "text":
        vals = model.params["values"][:n]
        return vals, [normalize_value_numeric(v) for v in vals]
    if model.rounding.get("type") == "scaled_int_exact":
        scale = model.rounding["scale"]
        ints = gen_int(model, n)
        nums = [i / scale for i in ints]
        # preserve as minimal strings via numeric rendering is risky; compare numerically
        return [str(x) for x in nums], nums
    # int_exact
    ints = gen_int(model, n)
    nums = [float(i) for i in ints]
    return [str(i) for i in ints], nums


def build_lab_entry(section: str, lab_name: str, page_title: str, max_level: int) -> Dict[str, Any]:
    rows = extract_lab_table(page_title)

    canon_rows = [{
        "level": r["level"],
        "time_min": r["time_min"],
        "cost_int": r["cost_int"],
        "value_text": r["value_text"],
        "value_num": r["value_num"],
    } for r in rows]

    rows_hash = sha256_canonical_rows(canon_rows)

    time_seq = [r["time_min"] for r in rows]
    cost_seq = [r["cost_int"] for r in rows]
    value_texts = [r["value_text"] for r in rows]
    value_nums = [r["value_num"] for r in rows]

    time_model = fit_best_int(time_seq)
    cost_model = fit_best_int(cost_seq)
    value_model = fit_value_model(value_texts, value_nums)

    # verification: regenerate and strict diff (minutes + ints + value strict)
    n = len(rows)
    if gen_int(time_model, n) != time_seq:
        raise RuntimeError("time_model mismatch")
    if gen_int(cost_model, n) != cost_seq:
        raise RuntimeError("cost_model mismatch")

    regen_value_text, regen_value_nums = regen_value(value_model, n)

    # value strictness:
    if value_model.rounding.get("type") == "text":
        if regen_value_text != value_texts:
            raise RuntimeError("value_text mismatch")
    else:
        # numeric strict
        if any(a is None or b is None or abs(a - b) > 0 for a, b in zip(regen_value_nums, value_nums)):
            raise RuntimeError("value_numeric mismatch")

    return {
        "section": section,
        "lab_name": lab_name,
        "page_title": page_title,
        "max_level": max_level,
        "source_url": f"https://the-tower-idle-tower-defense.fandom.com/wiki/{page_title}",
        "ground_truth": {
            "rows_hash_sha256": rows_hash,
            "row_count": n,
            "columns": ["level", "time_min", "cost_int", "value_text", "value_num"],
            "rows": canon_rows,
        },
        "models": {
            "time_min": time_model.__dict__,
            "cost_int": cost_model.__dict__,
            "value": value_model.__dict__,
        },
        "verification": {
            "status": "PASS",
            "time_minutes_strict": True,
            "cost_strict": True,
            "value_strict": True,
        },
    }


def main() -> int:
    sections = extract_all_sections_and_labs()

    out: Dict[str, Any] = {
        "source": {
            "title": "The Tower - Idle Tower Defense Wiki (Fandom) — Labs consolidated extract",
            "url": "https://the-tower-idle-tower-defense.fandom.com/wiki/Lab_Upgrades",
            "snapshot": "2026-01-19",
            "excerpt": "All lab sections and labs enumerated from Lab_Upgrades; each lab page parsed for Level/Time/Cost/Value table. Columns are compressed into exact models when possible and strictly verified.",
        },
        "meta": {
            "api": WIKI_API,
            "output_path": OUT_PATH,
            "pipeline": [
                "enumerate ALL lab sections + labs from Lab_Upgrades",
                "fetch each lab page via action=parse",
                "extract authoritative Level/Time/Cost/Value table",
                "fit smallest exact model per column (arith, geom, piecewise2, else lookup)",
                "hash canonical rows",
                "regenerate + strict diff verification",
            ],
        },
        "sections": {k: [{"lab_name": n, "page_title": p, "max_level": m} for (n, p, m) in v] for k, v in sections.items()},
        "labs": [],
    }

    failures: List[Dict[str, Any]] = []

    for section_name, labs in sections.items():
        for (lab_name, page_title, max_level) in labs:
            try:
                entry = build_lab_entry(section_name, lab_name, page_title, max_level)
            except Exception as e:
                entry = {
                    "section": section_name,
                    "lab_name": lab_name,
                    "page_title": page_title,
                    "max_level": max_level,
                    "source_url": f"https://the-tower-idle-tower-defense.fandom.com/wiki/{page_title}",
                    "verification": {"status": "FAIL", "error": str(e)},
                }
                failures.append(entry)
            out["labs"].append(entry)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=True)

    if failures:
        print(f"[FAIL] {len(failures)} labs failed extraction/verification. Output written: {OUT_PATH}")
        return 2

    print(f"[OK] All labs extracted + verified. Output written: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
