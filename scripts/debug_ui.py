from __future__ import annotations

import csv
import io
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
import streamlit as st


APP_PATH = Path(__file__).resolve()
REPO_ROOT = APP_PATH.parents[1] if APP_PATH.parent.name == "scripts" else APP_PATH.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass(frozen=True)
class SectionSpec:
    name: str
    header_col: int
    start_col: int
    end_col: int


SECTION_SPECS = [
    SectionSpec("Labs", 0, 0, 3),
    SectionSpec("WS", 4, 5, 16),
    SectionSpec("WS+", 17, 17, 24),
    SectionSpec("UWs", 25, 25, 29),
    SectionSpec("Cards", 30, 30, 37),
    SectionSpec("Relics", 38, 38, 40),
    SectionSpec("Vault", 41, 41, 42),
    SectionSpec("Bots", 44, 44, 48),
    SectionSpec("Themes & Songs", 50, 50, 51),
    SectionSpec("Modules", 53, 53, 71),
    SectionSpec("Guardians", 72, 72, 76),
    SectionSpec("Player & Stuff", 77, 77, 82),
]


# -----------------------------
# IDS parsing fallback
# -----------------------------

def _read_csv_rows_from_text(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


def _slice_row(row: list[str], start: int, end: int) -> list[str]:
    padded = row + [""] * max(0, end + 1 - len(row))
    return padded[start : end + 1]


def _row_has_data(row: Iterable[str]) -> bool:
    return any(str(cell).strip() != "" for cell in row)


def _collect_section_rows(rows: list[list[str]], spec: SectionSpec) -> list[list[str]]:
    out: list[list[str]] = []
    for row in rows[1:]:
        sliced = _slice_row(row, spec.start_col, spec.end_col)
        if _row_has_data(sliced):
            out.append(sliced)
    return out


def parse_ids_text(text: str) -> dict[str, dict]:
    rows = _read_csv_rows_from_text(text)
    if not rows:
        raise ValueError("IDS CSV is empty.")

    header = rows[0]
    sections: dict[str, dict] = {}

    for spec in SECTION_SPECS:
        expected = header[spec.header_col].strip() if spec.header_col < len(header) else ""
        if expected != spec.name:
            raise ValueError(
                f"Unexpected IDS header layout. Expected section {spec.name!r} at "
                f"column {spec.header_col}, found {expected!r}."
            )
        sections[spec.name] = {
            "header": _slice_row(header, spec.start_col, spec.end_col),
            "rows": _collect_section_rows(rows, spec),
        }
    return sections


# -----------------------------
# Helpers
# -----------------------------

def _safe_cell(row: list[str], idx: int) -> str:
    return row[idx].strip() if idx < len(row) else ""


def _as_text(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


# -----------------------------
# Raw IDS flatteners
# -----------------------------

def flatten_ids_levels(sections: dict[str, dict]) -> pd.DataFrame:
    records: list[dict] = []

    for row in sections["Labs"]["rows"]:
        name = _safe_cell(row, 0)
        if name:
            records.append({
                "section": "Labs",
                "family": "Lab",
                "name": name,
                "level": _safe_cell(row, 1),
                "target": _safe_cell(row, 2),
                "max": _safe_cell(row, 3),
                "preset": None,
                "attribute": None,
                "subtype": None,
            })

    workshop_presets = {"Farming": 1, "Tourney": 3, "Milestone": 5, "Preset 4": 7, "Preset 5": 9}
    for row in sections["WS"]["rows"]:
        name = _safe_cell(row, 0)
        if not name or name == "Workshop Upgrade":
            continue
        max_level = _safe_cell(row, 11)
        for preset, col in workshop_presets.items():
            records.append({
                "section": "WS",
                "family": "Workshop",
                "name": name,
                "level": _safe_cell(row, col),
                "target": None,
                "max": max_level,
                "preset": preset,
                "attribute": None,
                "subtype": None,
            })

    for row in sections["WS+"]["rows"][1:]:
        name = _safe_cell(row, 0)
        if name:
            records.append({
                "section": "WS+",
                "family": "Enhancement",
                "name": name,
                "level": _safe_cell(row, 1),
                "target": None,
                "max": _safe_cell(row, 2),
                "preset": None,
                "attribute": None,
                "subtype": None,
            })

    uw_rows = sections["UWs"]["rows"]
    for i in range(0, len(uw_rows), 4):
        block = uw_rows[i:i + 4]
        if len(block) < 4:
            continue
        uw_name = _safe_cell(block[0], 0)
        if not uw_name:
            continue
        for stat_row in block[:3]:
            records.append({
                "section": "UWs",
                "family": "Ultimate Weapon",
                "name": uw_name,
                "level": _safe_cell(stat_row, 4).split("|", 1)[0].strip(),
                "target": None,
                "max": None,
                "preset": None,
                "attribute": _safe_cell(stat_row, 2),
                "subtype": _safe_cell(stat_row, 3),
            })
        plus_name = _safe_cell(block[3], 2)
        if plus_name:
            records.append({
                "section": "UWs",
                "family": "UW+",
                "name": f"{uw_name}::{plus_name}",
                "level": _safe_cell(block[3], 4).split("|", 1)[0].strip(),
                "target": None,
                "max": None,
                "preset": None,
                "attribute": plus_name,
                "subtype": _safe_cell(block[3], 3),
            })

    for row in sections["Cards"]["rows"]:
        name = _safe_cell(row, 0)
        level = _safe_cell(row, 1)
        if name and level:
            records.append({
                "section": "Cards",
                "family": "Card",
                "name": name,
                "level": level,
                "target": None,
                "max": None,
                "preset": None,
                "attribute": None,
                "subtype": None,
            })

    for row in sections["Relics"]["rows"]:
        name = _safe_cell(row, 0)
        if name:
            records.append({
                "section": "Relics",
                "family": "Relic",
                "name": name,
                "level": _safe_cell(row, 1),
                "target": None,
                "max": None,
                "preset": None,
                "attribute": "Bonus",
                "subtype": None,
            })

    for row in sections["Vault"]["rows"]:
        name = _safe_cell(row, 0)
        if name:
            records.append({
                "section": "Vault",
                "family": "Vault",
                "name": name,
                "level": _safe_cell(row, 1),
                "target": None,
                "max": None,
                "preset": None,
                "attribute": "Bonus",
                "subtype": None,
            })

    current_bot = None
    for row in sections["Bots"]["rows"]:
        maybe_bot = _safe_cell(row, 0)
        if maybe_bot and maybe_bot not in {"true", "false"}:
            current_bot = maybe_bot
        attr = _safe_cell(row, 2)
        token = _safe_cell(row, 4)
        level = token.split("|", 1)[0].strip() if token else ""
        if current_bot and attr and level:
            records.append({
                "section": "Bots",
                "family": "Bot",
                "name": current_bot,
                "level": level,
                "target": None,
                "max": None,
                "preset": None,
                "attribute": attr,
                "subtype": None,
            })

    slot_names = ["Cannon", "Armor", "Generator", "Core"]
    starts = [0, 5, 10, 15]
    ends = [5, 10, 15, 99]
    module_rows = sections["Modules"]["rows"]

    def chunk(row: list[str], slot_index: int) -> list[str]:
        start = starts[slot_index]
        end = min(ends[slot_index], len(row))
        out = row[start:end]
        while len(out) < 5:
            out.append("")
        return out

    for slot_index, slot_name in enumerate(slot_names):
        slot_rows = [chunk(r, slot_index) for r in module_rows]
        idx = 16
        while idx < len(slot_rows):
            name = _safe_cell(slot_rows[idx], 0)
            if not name:
                idx += 1
                continue
            if idx + 2 >= len(slot_rows):
                break
            header_row = slot_rows[idx + 1]
            value_row = slot_rows[idx + 2]
            if _safe_cell(header_row, 0) != "Rarity" or _safe_cell(header_row, 1) != "Level":
                idx += 1
                continue
            records.append({
                "section": "Modules",
                "family": "Module",
                "name": name,
                "level": _safe_cell(value_row, 1),
                "target": None,
                "max": None,
                "preset": None,
                "attribute": slot_name,
                "subtype": _safe_cell(value_row, 0),
            })
            j = idx + 3
            while j < len(slot_rows):
                sub = slot_rows[j]
                label = _safe_cell(sub, 0)
                if label and j + 2 < len(slot_rows):
                    if _safe_cell(slot_rows[j + 1], 0) == "Rarity" and _safe_cell(slot_rows[j + 1], 1) == "Level":
                        break
                if label:
                    records.append({
                        "section": "Modules",
                        "family": "Module Substat",
                        "name": name,
                        "level": _safe_cell(sub, 3) or _safe_cell(sub, 2),
                        "target": None,
                        "max": None,
                        "preset": None,
                        "attribute": slot_name,
                        "subtype": label,
                    })
                j += 1
            idx = j

    for row in sections["Player & Stuff"]["rows"]:
        left_key = _safe_cell(row, 0)
        left_val = _safe_cell(row, 1)
        if left_key and left_key != "Tier":
            records.append({
                "section": "Player & Stuff",
                "family": "Player Meta",
                "name": left_key,
                "level": left_val,
                "target": None,
                "max": None,
                "preset": None,
                "attribute": None,
                "subtype": None,
            })
        right_key = _safe_cell(row, 4)
        right_val = _safe_cell(row, 5)
        if right_key and right_key != "Stat":
            records.append({
                "section": "Player & Stuff",
                "family": "Player Meta",
                "name": right_key,
                "level": right_val,
                "target": None,
                "max": None,
                "preset": None,
                "attribute": None,
                "subtype": None,
            })

    return pd.DataFrame.from_records(records)


# -----------------------------
# Compiled account-state support
# -----------------------------

def compile_account_state_from_text(ids_text: str):
    try:
        from parsers.ids_parser import parse_ids  # type: ignore
        from compilers.account_state_compiler import compile_account_state  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"Repo compiler imports failed: {exc}") from exc

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf-8-sig", delete=False) as handle:
        handle.write(ids_text)
        tmp_path = Path(handle.name)
    try:
        ids_raw = parse_ids(tmp_path)
        return compile_account_state(ids_raw)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass



def flatten_compiled_account_state(account_state) -> pd.DataFrame:
    records: list[dict] = []

    for name, level in sorted((account_state.labs or {}).items()):
        records.append({
            "family": "Lab",
            "name": name,
            "value": level,
            "detail": None,
            "preset": None,
            "source": "compiled_account_state.labs",
        })

    for name, entry in sorted((account_state.workshop or {}).items()):
        preset_levels = getattr(entry, "preset_levels", {}) or {}
        max_level = getattr(entry, "max_level", None)
        for preset, level in sorted(preset_levels.items()):
            records.append({
                "family": "Workshop",
                "name": name,
                "value": level,
                "detail": f"max={max_level}" if max_level is not None else None,
                "preset": preset,
                "source": "compiled_account_state.workshop",
            })

    ws_plus = getattr(account_state, "workshop_enhancements", None)
    if ws_plus is not None:
        for row in getattr(ws_plus, "rows", []) or []:
            name = row[0].strip() if len(row) > 0 else None
            level = row[1].strip() if len(row) > 1 else None
            max_level = row[2].strip() if len(row) > 2 else None
            if name:
                records.append({
                    "family": "Enhancement",
                    "name": name,
                    "value": level,
                    "detail": f"max={max_level}" if max_level else None,
                    "preset": None,
                    "source": "compiled_account_state.workshop_enhancements",
                })

    for name, snap in sorted((account_state.cards_inventory or {}).items()):
        records.append({
            "family": "Card",
            "name": name,
            "value": getattr(snap, "level", None),
            "detail": f"mastery_lab={getattr(snap, 'mastery_lab_level', None)}",
            "preset": None,
            "source": "compiled_account_state.cards_inventory",
        })

    for preset, cards in sorted((account_state.card_presets or {}).items()):
        for idx, card_name in enumerate(cards or [], start=1):
            records.append({
                "family": "Card Preset",
                "name": card_name,
                "value": idx,
                "detail": "slot_order",
                "preset": preset,
                "source": "compiled_account_state.card_presets",
            })

    for name, snap in sorted((account_state.modules_inventory or {}).items()):
        records.append({
            "family": "Module",
            "name": name,
            "value": getattr(snap, "level", None),
            "detail": f"slot={getattr(snap, 'slot_type', None)} | rarity={getattr(snap, 'rarity', None)}",
            "preset": None,
            "source": "compiled_account_state.modules_inventory",
        })
        for sub in getattr(snap, "substats", []) or []:
            records.append({
                "family": "Module Substat",
                "name": name,
                "value": _as_text(getattr(sub, "raw_token", None)) or _as_text(getattr(sub, "value", None)),
                "detail": getattr(sub, "name", None),
                "preset": None,
                "source": "compiled_account_state.modules_inventory.substats",
            })

    for preset, slot_map in sorted((account_state.module_presets or {}).items()):
        for slot_type, selection in sorted((slot_map or {}).items()):
            primary = getattr(selection, "primary", None)
            assist = getattr(selection, "assist", None)
            if primary:
                records.append({
                    "family": "Module Preset",
                    "name": primary,
                    "value": "primary",
                    "detail": slot_type,
                    "preset": preset,
                    "source": "compiled_account_state.module_presets",
                })
            if assist:
                records.append({
                    "family": "Module Preset",
                    "name": assist,
                    "value": "assist",
                    "detail": slot_type,
                    "preset": preset,
                    "source": "compiled_account_state.module_presets",
                })

    for name, snap in sorted((account_state.ultimate_weapons or {}).items()):
        track_levels = list(getattr(snap, "track_levels", []) or [])
        track_values = list(getattr(snap, "track_values", []) or [])
        for idx, token in enumerate(track_levels):
            detail = track_values[idx] if idx < len(track_values) else None
            records.append({
                "family": "Ultimate Weapon",
                "name": name,
                "value": token,
                "detail": detail,
                "preset": None,
                "source": "compiled_account_state.ultimate_weapons",
            })

    for key, snap in sorted((account_state.uw_plus_tracks or {}).items()):
        records.append({
            "family": "UW+",
            "name": key,
            "value": getattr(snap, "display_token", None),
            "detail": getattr(snap, "current_state", None),
            "preset": None,
            "source": "compiled_account_state.uw_plus_tracks",
        })

    for bot_name, upgrades in sorted((account_state.bot_upgrades or {}).items()):
        for attr, level in sorted((upgrades or {}).items()):
            records.append({
                "family": "Bot",
                "name": bot_name,
                "value": level,
                "detail": attr,
                "preset": None,
                "source": "compiled_account_state.bot_upgrades",
            })

    for name, value in sorted((account_state.relics or {}).items()):
        records.append({
            "family": "Relic",
            "name": name,
            "value": value,
            "detail": None,
            "preset": None,
            "source": "compiled_account_state.relics",
        })

    for name, value in sorted((account_state.vault or {}).items()):
        records.append({
            "family": "Vault",
            "name": name,
            "value": value,
            "detail": None,
            "preset": None,
            "source": "compiled_account_state.vault",
        })

    for name, value in sorted((account_state.player_meta or {}).items()):
        records.append({
            "family": "Player Meta",
            "name": name,
            "value": value,
            "detail": None,
            "preset": None,
            "source": "compiled_account_state.player_meta",
        })

    return pd.DataFrame.from_records(records)


# -----------------------------
# UI
# -----------------------------

st.set_page_config(page_title="TowerSim Debug UI", layout="wide")
st.title("TowerSim Debug UI")
st.caption("Hosted-first IDS source and compiled account-state inspector.")

uploaded_file = st.sidebar.file_uploader("Upload _IDS.csv", type=["csv"])
use_repo_default = st.sidebar.checkbox("Use repo default input/_IDS.csv if no upload is provided", value=True)

ids_text = None
source_label = None

if uploaded_file is not None:
    ids_text = uploaded_file.getvalue().decode("utf-8-sig", errors="replace")
    source_label = uploaded_file.name
elif use_repo_default:
    default_ids_path = REPO_ROOT / "input" / "_IDS.csv"
    if default_ids_path.exists():
        ids_text = default_ids_path.read_text(encoding="utf-8-sig")
        source_label = str(default_ids_path.relative_to(REPO_ROOT))

if ids_text is None:
    st.info("Upload an _IDS.csv file to begin.")
    st.stop()

st.sidebar.success(f"Loaded: {source_label}")

try:
    sections = parse_ids_text(ids_text)
except Exception as exc:
    st.error(f"Failed to parse IDS file: {exc}")
    st.stop()

ids_levels_df = flatten_ids_levels(sections)
compiled_df = pd.DataFrame()
compiled_error = None
try:
    compiled_state = compile_account_state_from_text(ids_text)
    compiled_df = flatten_compiled_account_state(compiled_state)
except Exception as exc:
    compiled_state = None
    compiled_error = str(exc)

tab_visual, tab_flat, tab_compiled, tab_raw = st.tabs([
    "IDS visual",
    "Flat IDS levels",
    "Compiled account state",
    "Raw sections",
])

with tab_visual:
    st.subheader("IDS visual")
    st.caption("Section-by-section source view following the IDS sheet mental model.")
    ordered_sections = [spec.name for spec in SECTION_SPECS]
    cols_per_row = 4
    for row_start in range(0, len(ordered_sections), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, section_name in zip(cols, ordered_sections[row_start: row_start + cols_per_row]):
            payload = sections.get(section_name, {"rows": []})
            rows = payload["rows"]
            with col:
                st.markdown(f"### {section_name}")
                st.caption(f"{len(rows)} rows")
                if not rows:
                    st.write("No data")
                    continue
                preview_records = []
                for row in rows[:50]:
                    preview_records.append({
                        "name": _safe_cell(row, 0),
                        "value": _safe_cell(row, 1),
                        "extra": _safe_cell(row, 2),
                    })
                st.dataframe(pd.DataFrame(preview_records), use_container_width=True, height=320)

with tab_flat:
    st.subheader("Flat IDS levels")
    st.caption("Flattened searchable ledger of level-like values directly from the IDS source shape.")
    if ids_levels_df.empty:
        st.write("No flattened IDS values found.")
    else:
        section_filter = st.multiselect(
            "Filter sections",
            options=sorted(ids_levels_df["section"].dropna().unique().tolist()),
            default=sorted(ids_levels_df["section"].dropna().unique().tolist()),
            key="ids_sections",
        )
        family_filter = st.multiselect(
            "Filter families",
            options=sorted(ids_levels_df["family"].dropna().unique().tolist()),
            default=sorted(ids_levels_df["family"].dropna().unique().tolist()),
            key="ids_families",
        )
        search_text = st.text_input("Search IDS rows", value="", key="ids_search").strip().lower()
        filtered = ids_levels_df[
            ids_levels_df["section"].isin(section_filter) & ids_levels_df["family"].isin(family_filter)
        ].copy()
        if search_text:
            mask = (
                filtered["name"].fillna("").astype(str).str.lower().str.contains(search_text)
                | filtered["attribute"].fillna("").astype(str).str.lower().str.contains(search_text)
                | filtered["subtype"].fillna("").astype(str).str.lower().str.contains(search_text)
            )
            filtered = filtered[mask]
        st.dataframe(filtered, use_container_width=True, height=720)

with tab_compiled:
    st.subheader("Compiled account state")
    st.caption("Normalized account interpretation from the repo compiler path. This is the best first-pass 'all my levels' surface.")
    if compiled_error:
        st.warning(f"Compiled account-state tab unavailable: {compiled_error}")
    elif compiled_df.empty:
        st.write("Compiled account-state returned no rows.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Compiled rows", len(compiled_df))
        c2.metric("Families", compiled_df["family"].nunique())
        c3.metric("Presets represented", compiled_df["preset"].dropna().nunique())
        family_filter = st.multiselect(
            "Filter compiled families",
            options=sorted(compiled_df["family"].dropna().unique().tolist()),
            default=sorted(compiled_df["family"].dropna().unique().tolist()),
            key="compiled_families",
        )
        preset_options = sorted([p for p in compiled_df["preset"].dropna().unique().tolist() if p])
        preset_filter = st.multiselect(
            "Filter compiled presets",
            options=preset_options,
            default=preset_options,
            key="compiled_presets",
        )
        search_text = st.text_input("Search compiled rows", value="", key="compiled_search").strip().lower()
        filtered = compiled_df[compiled_df["family"].isin(family_filter)].copy()
        if preset_options:
            filtered = filtered[(filtered["preset"].isna()) | (filtered["preset"].isin(preset_filter))]
        if search_text:
            mask = (
                filtered["name"].fillna("").astype(str).str.lower().str.contains(search_text)
                | filtered["detail"].fillna("").astype(str).str.lower().str.contains(search_text)
                | filtered["source"].fillna("").astype(str).str.lower().str.contains(search_text)
            )
            filtered = filtered[mask]
        st.dataframe(filtered, use_container_width=True, height=720)

with tab_raw:
    st.subheader("Raw sections")
    selected_section = st.selectbox("Section", [spec.name for spec in SECTION_SPECS])
    raw_rows = sections[selected_section]["rows"]
    if raw_rows:
        max_width = max(len(r) for r in raw_rows)
        padded_rows = [r + [""] * (max_width - len(r)) for r in raw_rows]
        raw_df = pd.DataFrame(padded_rows, columns=[f"col_{i}" for i in range(max_width)])
        st.dataframe(raw_df, use_container_width=True, height=720)
    else:
        st.write("No rows in this section.")
