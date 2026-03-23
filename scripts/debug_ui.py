
from __future__ import annotations

import csv
import io
import sys
import tempfile
from dataclasses import dataclass, asdict, is_dataclass
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

SECTION_COLORS = {
    "Labs": "#6ea8fe",
    "WS": "#7ee787",
    "WS+": "#d2a8ff",
    "UWs": "#ffb86b",
    "Cards": "#8be9fd",
    "Relics": "#f2cc60",
    "Vault": "#ff7b72",
    "Bots": "#79c0ff",
    "Themes & Songs": "#a5d6a7",
    "Modules": "#c9d1d9",
    "Guardians": "#ffa657",
    "Player & Stuff": "#f778ba",
}


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.35rem; padding-bottom: 1.0rem; max-width: 1500px;}
        .stApp, .block-container {font-size: 16px;}
        .ts-card {
            border: 1px solid rgba(255,255,255,0.10);
            border-left: 7px solid var(--accent);
            border-radius: 14px;
            padding: 0.9rem 0.95rem 0.7rem 0.95rem;
            margin-bottom: 1rem;
            background: linear-gradient(180deg, var(--accent-soft), rgba(255,255,255,0.03));
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
        }
        .ts-card h4 {
            margin: 0;
            font-size: 1.12rem;
            line-height: 1.2;
            letter-spacing: 0.01em;
        }
        .ts-card-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.55rem;
            gap: 0.5rem;
        }
        .ts-badge {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 999px;
            padding: 0.18rem 0.55rem;
            font-size: 0.76rem;
            color: rgba(255,255,255,0.86);
            white-space: nowrap;
        }
        .ts-muted {
            color: rgba(250,250,250,0.74);
            font-size: 0.85rem;
            margin-bottom: 0.45rem;
        }
        .ts-strip {
            display: flex;
            gap: 0.55rem;
            flex-wrap: wrap;
            margin: 0.35rem 0 0.9rem 0;
        }
        .ts-pill {
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 999px;
            padding: 0.28rem 0.62rem;
            font-size: 0.79rem;
            background: rgba(255,255,255,0.04);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
        }
        .ts-small-note {
            color: rgba(250,250,250,0.62);
            font-size: 0.78rem;
        }
        .ts-html-table-wrap {
            margin-top: 0.45rem;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 10px;
            overflow: hidden;
            background: color-mix(in srgb, var(--accent) 20%, rgba(10,14,24,0.96));
        }
        table.ts-html-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
            line-height: 1.35;
        }
        .ts-html-table thead th {
            text-align: left;
            font-weight: 700;
            padding: 0.55rem 0.7rem;
            background: color-mix(in srgb, var(--accent) 30%, rgba(16,20,30,0.98));
            border-bottom: 1px solid rgba(255,255,255,0.10);
        }
        .ts-html-table tbody td {
            padding: 0.48rem 0.7rem;
            border-top: 1px solid rgba(255,255,255,0.06);
            background: color-mix(in srgb, var(--accent) 16%, rgba(8,12,20,0.96));
            vertical-align: top;
            white-space: nowrap;
        }
        .ts-html-table tbody tr:nth-child(even) td {
            background: color-mix(in srgb, var(--accent) 20%, rgba(8,12,20,0.96));
        }
        .ts-preview-wrap {
            overflow: auto;
            max-height: var(--table-height);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 10px;
            background: rgba(0,0,0,0.10);
        }
        .ts-preview-wrap table {
            width: 100%;
            border-collapse: collapse;
            table-layout: auto;
            font-size: 0.95rem;
            line-height: 1.25;
        }
        .ts-preview-wrap thead th {
            position: sticky;
            top: 0;
            z-index: 1;
            background: rgba(255,255,255,0.06);
            color: rgba(255,255,255,0.82);
            font-weight: 600;
            text-align: left;
            padding: 0.55rem 0.7rem;
            border-bottom: 1px solid rgba(255,255,255,0.07);
            white-space: nowrap;
        }
        .ts-preview-wrap tbody td {
            padding: 0.52rem 0.7rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            vertical-align: top;
            white-space: nowrap;
        }
        .ts-preview-wrap tbody tr:hover td {
            background: rgba(255,255,255,0.025);
        }
        .ts-alert {
            border: 1px solid rgba(255,123,114,0.35);
            background: rgba(255,123,114,0.10);
            border-left: 6px solid #ff7b72;
            padding: 0.7rem 0.9rem;
            border-radius: 10px;
            margin: 0.4rem 0 1rem 0;
        }
        .ts-ok {
            border: 1px solid rgba(126,231,135,0.25);
            background: rgba(126,231,135,0.08);
            border-left: 6px solid #7ee787;
            padding: 0.55rem 0.8rem;
            border-radius: 10px;
            margin: 0.4rem 0 1rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def _safe_cell(row: list[str], idx: int) -> str:
    return row[idx].strip() if idx < len(row) else ""


def _as_text(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def flatten_ids_levels(sections: dict[str, dict]) -> pd.DataFrame:
    records: list[dict] = []

    for row in sections["Labs"]["rows"]:
        name = _safe_cell(row, 0)
        if name:
            records.append({"section": "Labs", "family": "Lab", "name": name, "level": _safe_cell(row, 1), "target": _safe_cell(row, 2), "max": _safe_cell(row, 3), "preset": None, "attribute": None, "subtype": None})

    workshop_presets = {"Farming": 1, "Tourney": 3, "Milestone": 5, "Preset 4": 7, "Preset 5": 9}
    for row in sections["WS"]["rows"]:
        name = _safe_cell(row, 0)
        if not name or name == "Workshop Upgrade":
            continue
        max_level = _safe_cell(row, 11)
        for preset, col in workshop_presets.items():
            records.append({"section": "WS", "family": "Workshop", "name": name, "level": _safe_cell(row, col), "target": None, "max": max_level, "preset": preset, "attribute": None, "subtype": None})

    for row in sections["WS+"]["rows"][1:]:
        name = _safe_cell(row, 0)
        if name:
            records.append({"section": "WS+", "family": "Enhancement", "name": name, "level": _safe_cell(row, 1), "target": None, "max": _safe_cell(row, 2), "preset": None, "attribute": None, "subtype": None})

    uw_rows = sections["UWs"]["rows"]
    for i in range(0, len(uw_rows), 4):
        block = uw_rows[i:i + 4]
        if len(block) < 4:
            continue
        uw_name = _safe_cell(block[0], 0)
        if not uw_name:
            continue
        for stat_row in block[:3]:
            records.append({"section": "UWs", "family": "Ultimate Weapon", "name": uw_name, "level": _safe_cell(stat_row, 4).split("|", 1)[0].strip(), "target": None, "max": None, "preset": None, "attribute": _safe_cell(stat_row, 2), "subtype": _safe_cell(stat_row, 3)})
        plus_name = _safe_cell(block[3], 2)
        if plus_name:
            records.append({"section": "UWs", "family": "UW+", "name": f"{uw_name}::{plus_name}", "level": _safe_cell(block[3], 4).split("|", 1)[0].strip(), "target": None, "max": None, "preset": None, "attribute": plus_name, "subtype": _safe_cell(block[3], 3)})

    for row in sections["Cards"]["rows"]:
        name = _safe_cell(row, 0)
        level = _safe_cell(row, 1)
        if name and level:
            records.append({"section": "Cards", "family": "Card", "name": name, "level": level, "target": None, "max": None, "preset": None, "attribute": None, "subtype": None})

    for row in sections["Relics"]["rows"]:
        name = _safe_cell(row, 0)
        if name:
            records.append({"section": "Relics", "family": "Relic", "name": name, "level": _safe_cell(row, 1), "target": None, "max": None, "preset": None, "attribute": "Bonus", "subtype": None})

    for row in sections["Vault"]["rows"]:
        name = _safe_cell(row, 0)
        if name:
            records.append({"section": "Vault", "family": "Vault", "name": name, "level": _safe_cell(row, 1), "target": None, "max": None, "preset": None, "attribute": "Bonus", "subtype": None})

    current_bot = None
    for row in sections["Bots"]["rows"]:
        maybe_bot = _safe_cell(row, 0)
        if maybe_bot and maybe_bot not in {"true", "false"}:
            current_bot = maybe_bot
        attr = _safe_cell(row, 2)
        token = _safe_cell(row, 4)
        level = token.split("|", 1)[0].strip() if token else ""
        if current_bot and attr and level:
            records.append({"section": "Bots", "family": "Bot", "name": current_bot, "level": level, "target": None, "max": None, "preset": None, "attribute": attr, "subtype": None})

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
            records.append({"section": "Modules", "family": "Module", "name": name, "level": _safe_cell(value_row, 1), "target": None, "max": None, "preset": None, "attribute": slot_name, "subtype": _safe_cell(value_row, 0)})
            j = idx + 3
            while j < len(slot_rows):
                sub = slot_rows[j]
                label = _safe_cell(sub, 0)
                if label and j + 2 < len(slot_rows):
                    if _safe_cell(slot_rows[j + 1], 0) == "Rarity" and _safe_cell(slot_rows[j + 1], 1) == "Level":
                        break
                if label:
                    records.append({"section": "Modules", "family": "Module Substat", "name": name, "level": _safe_cell(sub, 3) or _safe_cell(sub, 2), "target": None, "max": None, "preset": None, "attribute": slot_name, "subtype": label})
                j += 1
            idx = j

    for row in sections["Player & Stuff"]["rows"]:
        left_key = _safe_cell(row, 0)
        left_val = _safe_cell(row, 1)
        if left_key and left_key != "Tier":
            records.append({"section": "Player & Stuff", "family": "Player Meta", "name": left_key, "level": left_val, "target": None, "max": None, "preset": None, "attribute": None, "subtype": None})
        right_key = _safe_cell(row, 4)
        right_val = _safe_cell(row, 5)
        if right_key and right_key != "Stat":
            records.append({"section": "Player & Stuff", "family": "Player Meta", "name": right_key, "level": right_val, "target": None, "max": None, "preset": None, "attribute": None, "subtype": None})

    return pd.DataFrame.from_records(records)


def compile_account_state_from_text(ids_text: str, default_preset: str = "Farming"):
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
        return compile_account_state(ids_raw, default_preset=default_preset)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def compile_query_rows_from_text(ids_text: str, default_preset: str = "Farming", state_mode: str = "start_of_run", perk_state: str = "auto"):
    try:
        from parsers.ids_parser import parse_ids  # type: ignore
        from compilers.account_state_compiler import compile_account_state  # type: ignore
        from compilers.stat_input_compiler import compile_stat_inputs  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"Repo query-engine imports failed: {exc}") from exc

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf-8-sig", delete=False) as handle:
        handle.write(ids_text)
        tmp_path = Path(handle.name)
    try:
        ids_raw = parse_ids(tmp_path)
        state = compile_account_state(ids_raw, default_preset=default_preset)
        perk_flag = None if perk_state == "auto" else (perk_state == "on")
        rows = compile_stat_inputs(state, preset_name=default_preset, state_mode=state_mode, perks_enabled=perk_flag)
        return state, rows
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def flatten_compiled_account_state(account_state) -> pd.DataFrame:
    records: list[dict] = []

    for name, level in sorted((account_state.labs or {}).items()):
        records.append({"section": "Labs", "family": "Lab", "name": name, "value": level, "detail": None, "preset": None, "source": "compiled_account_state.labs"})

    for name, entry in sorted((account_state.workshop or {}).items()):
        preset_levels = getattr(entry, "preset_levels", {}) or {}
        max_level = getattr(entry, "max_level", None)
        for preset, level in sorted(preset_levels.items()):
            records.append({"section": "Workshop", "family": "Workshop", "name": name, "value": level, "detail": f"max={max_level}" if max_level is not None else None, "preset": preset, "source": "compiled_account_state.workshop"})

    ws_plus = getattr(account_state, "workshop_enhancements", None)
    if ws_plus is not None:
        for row in getattr(ws_plus, "rows", []) or []:
            name = row[0].strip() if len(row) > 0 else None
            level = row[1].strip() if len(row) > 1 else None
            max_level = row[2].strip() if len(row) > 2 else None
            if name:
                records.append({"section": "Enhancements", "family": "Enhancement", "name": name, "value": level, "detail": f"max={max_level}" if max_level else None, "preset": None, "source": "compiled_account_state.workshop_enhancements"})

    for name, snap in sorted((account_state.cards_inventory or {}).items()):
        records.append({"section": "Cards", "family": "Card", "name": name, "value": getattr(snap, "level", None), "detail": f"mastery_lab={getattr(snap, 'mastery_lab_level', None)}", "preset": None, "source": "compiled_account_state.cards_inventory"})

    for preset, cards in sorted((account_state.card_presets or {}).items()):
        for idx, card_name in enumerate(cards or [], start=1):
            records.append({"section": "Cards", "family": "Card Preset", "name": card_name, "value": idx, "detail": "slot_order", "preset": preset, "source": "compiled_account_state.card_presets"})

    for name, snap in sorted((account_state.modules_inventory or {}).items()):
        records.append({"section": "Modules", "family": "Module", "name": name, "value": getattr(snap, "level", None), "detail": f"slot={getattr(snap, 'slot_type', None)} | rarity={getattr(snap, 'rarity', None)}", "preset": None, "source": "compiled_account_state.modules_inventory"})
        for sub in getattr(snap, "substats", []) or []:
            records.append({"section": "Modules", "family": "Module Substat", "name": name, "value": _as_text(getattr(sub, "raw_token", None)) or _as_text(getattr(sub, "value", None)), "detail": getattr(sub, "name", None), "preset": None, "source": "compiled_account_state.modules_inventory.substats"})

    for preset, slot_map in sorted((account_state.module_presets or {}).items()):
        for slot_type, selection in sorted((slot_map or {}).items()):
            primary = getattr(selection, "primary", None)
            assist = getattr(selection, "assist", None)
            if primary:
                records.append({"section": "Modules", "family": "Module Preset", "name": primary, "value": "primary", "detail": slot_type, "preset": preset, "source": "compiled_account_state.module_presets"})
            if assist:
                records.append({"section": "Modules", "family": "Module Preset", "name": assist, "value": "assist", "detail": slot_type, "preset": preset, "source": "compiled_account_state.module_presets"})

    for name, snap in sorted((account_state.ultimate_weapons or {}).items()):
        track_levels = list(getattr(snap, "track_levels", []) or [])
        track_values = list(getattr(snap, "track_values", []) or [])
        for idx, token in enumerate(track_levels):
            detail = track_values[idx] if idx < len(track_values) else None
            records.append({"section": "UWs", "family": "Ultimate Weapon", "name": name, "value": token, "detail": detail, "preset": None, "source": "compiled_account_state.ultimate_weapons"})

    for key, snap in sorted((account_state.uw_plus_tracks or {}).items()):
        records.append({"section": "UWs", "family": "UW+", "name": key, "value": getattr(snap, "display_token", None), "detail": getattr(snap, "current_state", None), "preset": None, "source": "compiled_account_state.uw_plus_tracks"})

    for bot_name, upgrades in sorted((account_state.bot_upgrades or {}).items()):
        for attr, level in sorted((upgrades or {}).items()):
            records.append({"section": "Bots", "family": "Bot", "name": bot_name, "value": level, "detail": attr, "preset": None, "source": "compiled_account_state.bot_upgrades"})

    for name, value in sorted((account_state.relics or {}).items()):
        records.append({"section": "Relics", "family": "Relic", "name": name, "value": value, "detail": None, "preset": None, "source": "compiled_account_state.relics"})

    for name, value in sorted((account_state.vault or {}).items()):
        records.append({"section": "Vault", "family": "Vault", "name": name, "value": value, "detail": None, "preset": None, "source": "compiled_account_state.vault"})

    for name, value in sorted((account_state.player_meta or {}).items()):
        records.append({"section": "Meta", "family": "Player Meta", "name": name, "value": value, "detail": None, "preset": None, "source": "compiled_account_state.player_meta"})

    for preset_name in [
        getattr(account_state, "active_card_preset", None),
        getattr(account_state, "active_module_preset", None),
        getattr(account_state, "active_perk_preset", None),
        getattr(account_state, "default_preset", None),
    ]:
        if preset_name:
            records.append({"section": "Meta", "family": "Preset", "name": "Active/Default Preset", "value": preset_name, "detail": None, "preset": None, "source": "compiled_account_state.presets"})

    return pd.DataFrame.from_records(records)


def flatten_query_rows(rows) -> pd.DataFrame:
    records: list[dict] = []
    for row in rows:
        data = {}
        if is_dataclass(row):
            try:
                data = asdict(row)
            except Exception:
                data = {name: getattr(row, name, None) for name in getattr(row, "__dataclass_fields__", {}).keys()}
        else:
            data = dict(getattr(row, "__dict__", {}))

        source_family = data.get("source_family")
        section = _query_section_for_family(str(source_family or ""))
        dest_type = data.get("destination_object_type")
        dest_id = data.get("destination_id")
        records.append(
            {
                "section": section,
                "source_family": source_family,
                "source_name": data.get("source_name"),
                "stat_name": data.get("stat_name"),
                "value": data.get("value"),
                "value_type": data.get("value_type"),
                "stage": data.get("stage"),
                "preset_name": data.get("preset_name"),
                "destination": f"{dest_type}::{dest_id}" if dest_type and dest_id else None,
                "destination_object_type": dest_type,
                "destination_id": dest_id,
                "contributor_id": data.get("contributor_id"),
                "resolver_id": data.get("resolver_id"),
                "kb_mapped": data.get("kb_mapped"),
                "notes": data.get("notes"),
                "provenance": data.get("provenance"),
            }
        )
    return pd.DataFrame.from_records(records)


def _query_section_for_family(source_family: str) -> str:
    family = source_family.lower().strip()
    if family in {"lab"}:
        return "QE Labs"
    if family in {"workshop"}:
        return "QE Workshop"
    if family in {"enhancement", "theme_song", "player_stuff"}:
        return "QE Enhancements"
    if family in {"uw", "uw_plus", "uw_unlock"}:
        return "QE UWs"
    if family in {"card"}:
        return "QE Cards"
    if family in {"module", "module_substat"}:
        return "QE Modules"
    if family in {"bot", "bot_unlock", "guardian"}:
        return "QE Bots"
    if family in {"relic", "vault"}:
        return "QE Relics/Vault"
    if family in {"perk"}:
        return "QE Perks"
    return "QE Other"


def _top_counts(df: pd.DataFrame, group_col: str, topn: int = 6) -> pd.DataFrame:
    if df.empty or group_col not in df.columns:
        return pd.DataFrame(columns=[group_col, "rows"])
    out = df[group_col].fillna("(blank)").value_counts().head(topn).rename_axis(group_col).reset_index(name="rows")
    return out



def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    value = hex_color.lstrip("#")
    if len(value) != 6:
        return f"rgba(121,192,255,{alpha})"
    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _clean_max_detail(value) -> Optional[str]:
    text = _as_text(value)
    if not text:
        return None
    return text.replace("max=", "")


def _render_preview_html(df: pd.DataFrame, accent: str, height: int = 320):
    if df is None or df.empty:
        st.write("No data")
        return
    show = df.fillna("").astype(str).copy()
    html = show.to_html(index=False, escape=False, border=0)
    st.markdown(
        f'<div class="ts-preview-wrap" style="--table-height:{height}px; --accent:{accent};">{html}</div>',
        unsafe_allow_html=True,
    )


def _status_banner(kind: str, message: str):
    klass = "ts-ok" if kind == "ok" else "ts-alert"
    st.markdown(f'<div class="{klass}">{message}</div>', unsafe_allow_html=True)


def _card_open(section_name: str):
    base_name = section_name.replace("QE ", "").replace("/Vault", "")
    color = SECTION_COLORS.get(base_name, "#79c0ff")
    soft = _hex_to_rgba(color, 0.10)
    st.markdown(
        f'<div class="ts-card" style="--accent:{color}; --accent-soft:{soft};"><div class="ts-card-head"><h4>{section_name}</h4></div>',
        unsafe_allow_html=True,
    )


def _card_close():
    st.markdown("</div>", unsafe_allow_html=True)


def _render_table(df: pd.DataFrame, height: int = 280):
    st.dataframe(df, use_container_width=True, height=height, hide_index=True)


def ids_preview_df(section_name: str, rows: list[list[str]]) -> pd.DataFrame:
    records = []
    if section_name == "Labs":
        for row in rows[:40]:
            records.append({"Lab": _safe_cell(row, 0), "Level": _safe_cell(row, 1), "Target": _safe_cell(row, 2), "Max": _safe_cell(row, 3)})
    elif section_name == "WS":
        for row in rows[:40]:
            if not _safe_cell(row, 0):
                continue
            records.append({"Upgrade": _safe_cell(row, 0), "Farm": _safe_cell(row, 1), "Tour": _safe_cell(row, 3), "Milestone": _safe_cell(row, 5), "Max": _safe_cell(row, 11)})
    elif section_name == "WS+":
        for row in rows[1:41]:
            records.append({"Enhancement": _safe_cell(row, 0), "Value": _safe_cell(row, 1), "Level": _safe_cell(row, 2), "Extra": _safe_cell(row, 3)})
    elif section_name == "UWs":
        uw_rows = rows[:16]
        for i in range(0, len(uw_rows), 4):
            block = uw_rows[i:i + 4]
            if len(block) < 4:
                continue
            uw_name = _safe_cell(block[0], 0)
            for stat_row in block[:3]:
                records.append({"Weapon": uw_name, "Attribute": _safe_cell(stat_row, 2), "Value": _safe_cell(stat_row, 3), "Level": _safe_cell(stat_row, 4).split("|", 1)[0].strip()})
    elif section_name == "Cards":
        for row in rows[:40]:
            records.append({"Card": _safe_cell(row, 0), "Level": _safe_cell(row, 1), "Mastery": _safe_cell(row, 2), "Farm": _safe_cell(row, 3), "Tour": _safe_cell(row, 4)})
    elif section_name == "Relics":
        for row in rows[:40]:
            records.append({"Relic": _safe_cell(row, 0), "Bonus": _safe_cell(row, 1), "Extra": _safe_cell(row, 2)})
    elif section_name == "Vault":
        for row in rows[:40]:
            records.append({"Vault Item": _safe_cell(row, 0), "Value": _safe_cell(row, 1)})
    elif section_name == "Bots":
        current_bot = None
        for row in rows[:40]:
            maybe_bot = _safe_cell(row, 0)
            if maybe_bot and maybe_bot not in {"true", "false"}:
                current_bot = maybe_bot
            records.append({"Bot": current_bot, "Status": _safe_cell(row, 0), "Attribute": _safe_cell(row, 2), "Value": _safe_cell(row, 4)})
    elif section_name == "Modules":
        slot_names = ["Cannon", "Armor", "Generator", "Core"]
        starts = [0, 5, 10, 15]
        ends = [5, 10, 15, 99]
        def chunk(row, idx):
            start = starts[idx]
            end = min(ends[idx], len(row))
            out = row[start:end]
            while len(out) < 5:
                out.append("")
            return out
        for slot_index, slot_name in enumerate(slot_names):
            slot_rows = [chunk(r, slot_index) for r in rows]
            idx = 16
            while idx < len(slot_rows) and len(records) < 40:
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
                records.append({"Module": name, "Slot": slot_name, "Level": _safe_cell(value_row, 1), "Rarity": _safe_cell(value_row, 0), "Main Stat": _safe_cell(value_row, 2)})
                idx += 3
    elif section_name == "Player & Stuff":
        for row in rows[:40]:
            left_key = _safe_cell(row, 0)
            if left_key and left_key != "Tier":
                records.append({"Field": left_key, "Value": _safe_cell(row, 1)})
            right_key = _safe_cell(row, 4)
            if right_key and right_key != "Stat":
                records.append({"Field": right_key, "Value": _safe_cell(row, 5)})
    else:
        for row in rows[:40]:
            records.append({"Column 1": _safe_cell(row, 0), "Column 2": _safe_cell(row, 1), "Column 3": _safe_cell(row, 2)})
    return pd.DataFrame.from_records(records)


def compiled_preview_df(section_name: str, df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["section"] == section_name].copy()
    if df.empty:
        return pd.DataFrame()
    if section_name == "Labs":
        return df[["name", "value"]].rename(columns={"name": "Lab", "value": "Level"}).head(18)
    if section_name == "Workshop":
        pivot = (
            df[df["family"] == "Workshop"][["name", "preset", "value", "detail"]]
            .assign(Max=lambda x: x["detail"].map(_clean_max_detail))
            .drop(columns=["detail"])
            .pivot_table(index=["name", "Max"], columns="preset", values="value", aggfunc="first")
            .reset_index()
            .rename(columns={"name": "Upgrade"})
        )
        cols = [c for c in ["Upgrade", "Farming", "Tourney", "Milestone", "Preset 4", "Preset 5", "Max"] if c in pivot.columns]
        return pivot[cols].head(18)
    if section_name == "Enhancements":
        clean = df.copy()
        clean["Max"] = clean["detail"].map(_clean_max_detail)
        return clean[["name", "value", "Max"]].rename(columns={"name": "Enhancement", "value": "Value"}).head(18)
    if section_name == "UWs":
        return df[["family", "name", "value", "detail"]].rename(columns={"family": "Type", "name": "Name", "value": "Level", "detail": "Current"}).head(18)
    if section_name == "Cards":
        return df[["family", "name", "value", "preset", "detail"]].rename(columns={"family": "Type", "name": "Card", "value": "Value", "preset": "Preset", "detail": "Detail"}).head(18)
    if section_name == "Modules":
        out = df[["family", "name", "value", "preset", "detail"]].rename(columns={"family": "Type", "name": "Name", "value": "Value", "preset": "Preset", "detail": "Detail"}).head(18)
        return out
    if section_name == "Bots":
        return df[["name", "detail", "value"]].rename(columns={"name": "Bot", "detail": "Attribute", "value": "Level"}).head(18)
    if section_name in {"Relics", "Vault", "Meta"}:
        nice = df[["family", "name", "value", "detail"]].rename(columns={"family": "Type", "name": "Name", "value": "Value", "detail": "Detail"}).copy()
        if "Detail" in nice.columns:
            nice["Detail"] = nice["Detail"].fillna("")
        return nice.head(18)
    return df.head(18)



def query_preview_df(section_name: str, df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["section"] == section_name].copy()
    if df.empty:
        return pd.DataFrame()
    cols = ["source_name", "stat_name", "value", "value_type", "destination", "kb_mapped"]
    nice = df[cols].rename(columns={
        "source_name": "Source",
        "stat_name": "Stat",
        "value": "Value",
        "value_type": "Type",
        "destination": "Destination",
        "kb_mapped": "Mapped",
    }).copy()
    nice["Mapped"] = nice["Mapped"].fillna(False).map(lambda x: "Yes" if bool(x) else "No")
    return nice.head(18)




def _render_html_table(df: pd.DataFrame, section_name: str, max_rows: int = 40):
    if df is None or df.empty:
        st.write("No data")
        return
    display_df = df.head(max_rows).copy()
    cols = list(display_df.columns)
    thead = "".join(f"<th>{str(c)}</th>" for c in cols)
    body_rows = []
    for _, row in display_df.iterrows():
        cells = []
        for c in cols:
            val = row[c]
            sval = "" if pd.isna(val) else str(val)
            sval = (
                sval.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            cells.append(f"<td>{sval}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    body = "".join(body_rows)
    color = SECTION_COLORS.get(section_name.replace("QE ", "").replace("/Vault", ""), "#79c0ff")
    html_block = f"""
    <div class="ts-html-table-wrap" style="--accent:{color};">
        <table class="ts-html-table">
            <thead><tr>{thead}</tr></thead>
            <tbody>{body}</tbody>
        </table>
    </div>
    """
    st.markdown(html_block, unsafe_allow_html=True)


def _metrics_row(items: list[tuple[str, str | int | float]]):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)

def _safe_pct(n: int, d: int) -> str:
    return "0%" if d == 0 else f"{round(100.0 * n / d, 1)}%"



st.set_page_config(page_title="TowerSim Debug UI", layout="wide")
_inject_css()
st.title("TowerSim Debug UI")
st.caption("IDS, compiled account state, and query-prep inspector.")

preset_options = ["Farming", "Tourney", "Milestone", "Preset 4", "Preset 5"]
selected_preset = st.sidebar.selectbox("Preset", options=preset_options, index=0)
selected_state_mode = st.sidebar.selectbox("Query state mode", options=["start_of_run", "max_progression"], index=0)
selected_perk_state = st.sidebar.selectbox("Perk materialization", options=["auto", "on", "off"], index=0)

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
st.sidebar.markdown("---")
st.sidebar.markdown("**Active view context**")
st.sidebar.markdown(f"- Preset: `{selected_preset}`")
st.sidebar.markdown(f"- State mode: `{selected_state_mode}`")
st.sidebar.markdown(f"- Perks: `{selected_perk_state}`")

try:
    sections = parse_ids_text(ids_text)
except Exception as exc:
    st.error(f"Failed to parse IDS file: {exc}")
    st.stop()

ids_levels_df = flatten_ids_levels(sections)

compiled_df = pd.DataFrame()
compiled_error = None
try:
    compiled_state = compile_account_state_from_text(ids_text, default_preset=selected_preset)
    compiled_df = flatten_compiled_account_state(compiled_state)
except Exception as exc:
    compiled_state = None
    compiled_error = str(exc)

qe_df = pd.DataFrame()
qe_error = None
try:
    qe_state, qe_rows = compile_query_rows_from_text(
        ids_text,
        default_preset=selected_preset,
        state_mode=selected_state_mode,
        perk_state=selected_perk_state,
    )
    qe_df = flatten_query_rows(qe_rows)
except Exception as exc:
    qe_state = None
    qe_error = str(exc)

top_cols = st.columns(5)
top_cols[0].metric("IDS rows", int(len(ids_levels_df)))
top_cols[1].metric("Compiled rows", int(len(compiled_df)) if not compiled_df.empty else 0)
top_cols[2].metric("QE rows", int(len(qe_df)) if not qe_df.empty else 0)
top_cols[3].metric("QE mapped", int(qe_df["kb_mapped"].fillna(False).astype(bool).sum()) if not qe_df.empty else 0)
top_cols[4].metric("QE mapped %", _safe_pct(int(qe_df["kb_mapped"].fillna(False).astype(bool).sum()) if not qe_df.empty else 0, int(len(qe_df))))

if qe_error:
    st.warning(f"Global note: query engine unavailable: {qe_error}. If this mentions yaml, add pyyaml to root requirements.txt and redeploy.")

if compiled_error:
    _status_banner("error", f"<strong>Compiled account state unavailable.</strong><br>{compiled_error}")
if qe_error:
    _status_banner("error", f"<strong>Query engine unavailable.</strong><br>{qe_error}")

tab_compiled_visual, tab_qe_visual, tab_qe_table, tab_compiled_table, tab_ids_visual, tab_ids_table = st.tabs([
    "Compiled visual",
    "Query engine visual",
    "Query engine table",
    "Compiled table",
    "IDS visual",
    "IDS table",
])

with tab_compiled_visual:
    st.subheader("Compiled visual")
    st.caption("Normalized account-state interpretation grouped into readable sections.")
    if compiled_error:
        st.warning(f"Compiled account-state unavailable: {compiled_error}")
    elif compiled_df.empty:
        st.write("Compiled account-state returned no rows.")
    else:
        _metrics_row([
            ("Compiled rows", int(len(compiled_df))),
            ("Families", int(compiled_df["family"].nunique())),
            ("Sections", int(compiled_df["section"].nunique())),
        ])
        counts = _top_counts(compiled_df, "section", topn=20)
        if not counts.empty:
            st.markdown('<div class="ts-strip">' + "".join([f'<span class="ts-pill">{r.section}: {int(r.rows)}</span>' for r in counts.itertuples()]) + '</div>', unsafe_allow_html=True)
        section_order = ["Labs", "Workshop", "Enhancements", "UWs", "Cards", "Modules", "Bots", "Relics", "Vault", "Meta"]
        cols_per_row = 2
        for row_start in range(0, len(section_order), cols_per_row):
            cols = st.columns(cols_per_row)
            for col, section_name in zip(cols, section_order[row_start: row_start + cols_per_row]):
                with col:
                    _card_open(section_name)
                    section_rows = compiled_df[compiled_df["section"] == section_name]
                    st.markdown(f'<div class="ts-muted">{len(section_rows)} compiled rows</div>', unsafe_allow_html=True)
                    preview = compiled_preview_df(section_name, compiled_df)
                    _render_preview_html(preview, SECTION_COLORS.get(section_name, "#79c0ff"), height=360)
                    _card_close()

with tab_qe_visual:
    st.subheader("Query engine visual")
    st.caption("Query-prep rows from compile_stat_inputs grouped by source family and destination flow.")
    if qe_error:
        st.warning(f"Query engine view unavailable: {qe_error}. If this mentions yaml, add pyyaml to root requirements.txt and redeploy.")
    elif qe_df.empty:
        st.write("No query rows found.")
    else:
        mapped_true = int(qe_df["kb_mapped"].fillna(False).astype(bool).sum())
        _metrics_row([
            ("QE rows", int(len(qe_df))),
            ("Families", int(qe_df["source_family"].nunique())),
            ("KB mapped", mapped_true),
            ("Mapped %", _safe_pct(mapped_true, int(len(qe_df)))),
        ])
        counts = _top_counts(qe_df, "section", topn=20)
        if not counts.empty:
            st.markdown('<div class="ts-strip">' + "".join([f'<span class="ts-pill">{r.section}: {int(r.rows)}</span>' for r in counts.itertuples()]) + '</div>', unsafe_allow_html=True)
        section_order = ["QE Labs", "QE Workshop", "QE Enhancements", "QE UWs", "QE Cards", "QE Modules", "QE Bots", "QE Relics/Vault", "QE Perks", "QE Other"]
        cols_per_row = 2
        for row_start in range(0, len(section_order), cols_per_row):
            cols = st.columns(cols_per_row)
            for col, section_name in zip(cols, section_order[row_start: row_start + cols_per_row]):
                with col:
                    _card_open(section_name)
                    section_rows = qe_df[qe_df["section"] == section_name]
                    mapped_section = int(section_rows["kb_mapped"].fillna(False).astype(bool).sum()) if not section_rows.empty else 0
                    st.markdown(f'<div class="ts-muted">{len(section_rows)} query rows · mapped {mapped_section}</div>', unsafe_allow_html=True)
                    preview = query_preview_df(section_name, qe_df)
                    base = section_name.replace("QE ", "").replace("/Vault", "")
                    _render_preview_html(preview, SECTION_COLORS.get(base, "#79c0ff"), height=360)
                    _card_close()

with tab_qe_table:
    st.subheader("Query engine table")
    st.caption("Full compile_stat_inputs ledger with routing and KB-mapped status.")
    if qe_error:
        st.warning(f"Query engine view unavailable: {qe_error}. If this mentions yaml, add pyyaml to root requirements.txt and redeploy.")
    elif qe_df.empty:
        st.write("No query rows found.")
    else:
        a, b, c = st.columns(3)
        section_filter = a.multiselect("QE sections", options=sorted(qe_df["section"].dropna().unique().tolist()), default=sorted(qe_df["section"].dropna().unique().tolist()))
        family_filter = b.multiselect("QE source families", options=sorted(qe_df["source_family"].dropna().unique().tolist()), default=sorted(qe_df["source_family"].dropna().unique().tolist()))
        mapped_filter = c.selectbox("KB mapped", options=["All", "True", "False"])
        search_text = st.text_input("Search QE rows", value="", key="qe_search").strip().lower()
        filtered = qe_df[qe_df["section"].isin(section_filter) & qe_df["source_family"].isin(family_filter)].copy()
        if mapped_filter != "All":
            flag = mapped_filter == "True"
            filtered = filtered[filtered["kb_mapped"].fillna(False).astype(bool) == flag]
        if search_text:
            mask = (
                filtered["source_name"].fillna("").astype(str).str.lower().str.contains(search_text)
                | filtered["stat_name"].fillna("").astype(str).str.lower().str.contains(search_text)
                | filtered["destination"].fillna("").astype(str).str.lower().str.contains(search_text)
                | filtered["notes"].fillna("").astype(str).str.lower().str.contains(search_text)
            )
            filtered = filtered[mask]
        _render_table(filtered, height=760)

with tab_compiled_table:
    st.subheader("Compiled table")
    st.caption("Full compiled account-state ledger.")
    if compiled_error:
        st.warning(f"Compiled account-state unavailable: {compiled_error}")
    elif compiled_df.empty:
        st.write("No compiled rows found.")
    else:
        a, b = st.columns(2)
        section_filter = a.multiselect("Compiled sections", options=sorted(compiled_df["section"].dropna().unique().tolist()), default=sorted(compiled_df["section"].dropna().unique().tolist()))
        family_filter = b.multiselect("Compiled families", options=sorted(compiled_df["family"].dropna().unique().tolist()), default=sorted(compiled_df["family"].dropna().unique().tolist()))
        search_text = st.text_input("Search compiled rows", value="", key="compiled_search").strip().lower()
        filtered = compiled_df[compiled_df["section"].isin(section_filter) & compiled_df["family"].isin(family_filter)].copy()
        if search_text:
            mask = (
                filtered["name"].fillna("").astype(str).str.lower().str.contains(search_text)
                | filtered["detail"].fillna("").astype(str).str.lower().str.contains(search_text)
                | filtered["source"].fillna("").astype(str).str.lower().str.contains(search_text)
            )
            filtered = filtered[mask]
        _render_table(filtered, height=760)

with tab_ids_visual:
    st.subheader("IDS visual")
    st.caption("Source-level view grouped by IDS section with readable section-specific headers.")
    _metrics_row([
        ("Sections", len(SECTION_SPECS)),
        ("IDS rows", int(sum(len(sections[s.name]["rows"]) for s in SECTION_SPECS))),
        ("Flat rows", int(len(ids_levels_df))),
    ])
    ordered_sections = [spec.name for spec in SECTION_SPECS]
    cols_per_row = 3
    for row_start in range(0, len(ordered_sections), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, section_name in zip(cols, ordered_sections[row_start: row_start + cols_per_row]):
            with col:
                _card_open(section_name)
                rows = sections.get(section_name, {"rows": []})["rows"]
                st.markdown(f'<div class="ts-muted">{len(rows)} source rows</div>', unsafe_allow_html=True)
                preview = ids_preview_df(section_name, rows)
                _render_preview_html(preview, SECTION_COLORS.get(section_name, "#79c0ff"), height=320)
                _card_close()

with tab_ids_table:
    st.subheader("IDS table")
    st.caption("Flattened searchable ledger of level-like values from the IDS source shape.")
    if ids_levels_df.empty:
        st.write("No IDS rows found.")
    else:
        a, b = st.columns(2)
        section_filter = a.multiselect("Sections", options=sorted(ids_levels_df["section"].dropna().unique().tolist()), default=sorted(ids_levels_df["section"].dropna().unique().tolist()))
        family_filter = b.multiselect("Families", options=sorted(ids_levels_df["family"].dropna().unique().tolist()), default=sorted(ids_levels_df["family"].dropna().unique().tolist()))
        search_text = st.text_input("Search IDS rows", value="", key="ids_search").strip().lower()
        filtered = ids_levels_df[ids_levels_df["section"].isin(section_filter) & ids_levels_df["family"].isin(family_filter)].copy()
        if search_text:
            mask = (
                filtered["name"].fillna("").astype(str).str.lower().str.contains(search_text)
                | filtered["attribute"].fillna("").astype(str).str.lower().str.contains(search_text)
                | filtered["subtype"].fillna("").astype(str).str.lower().str.contains(search_text)
            )
            filtered = filtered[mask]
        _render_table(filtered, height=760)
