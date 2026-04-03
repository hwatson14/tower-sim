"""
input/state_builder.py — Runtime-state assembly logic.

Owns: build_runtime_state() and private parsing/build helpers that assemble
AccountState from IdsRaw and manual overrides.

This module is the canonical builder implementation for input/runtime_state.py.
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from input.state_types import (
    AccountState,
    BotUpgradeSnapshot,
    CardSnapshot,
    GuardianTrackSnapshot,
    ModulePresetSelection,
    ModuleSnapshot,
    ModuleSubstat,
    ModuleSystemState,
    PerkSelection,
    TableSnapshot,
    UltimateWeaponSnapshot,
    UwTrackSnapshot,
    UwPlusTrackSnapshot,
    WorkshopEnhancementSnapshot,
    WorkshopEntrySnapshot,
)
from input.ids_parser import IdsRaw
ROOT = Path(__file__).resolve().parents[1]
_PRESET_CONTRACT_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'preset_contract.yaml'
_SECTION_LAYOUT_CONTRACT_PATH = ROOT / 'kb' / 'global-rules' / 'contracts' / 'section_layout_contract.yaml'


@lru_cache(maxsize=1)
def _load_preset_contract() -> dict[str, Any]:
    with _PRESET_CONTRACT_PATH.open('r', encoding='utf-8') as handle:
        raw = yaml.safe_load(handle) or {}
    canonical_presets = tuple(str(name) for name in raw.get('canonical_presets') or ())
    aliases = {str(key): str(value) for key, value in (raw.get('aliases') or {}).items()}
    if not canonical_presets:
        raise ValueError('Preset contract missing canonical_presets.')
    for alias_target in aliases.values():
        if alias_target not in canonical_presets:
            raise ValueError(f'Preset contract alias targets unknown canonical preset {alias_target!r}.')
    return {
        'canonical_presets': canonical_presets,
        'aliases': aliases,
    }


@lru_cache(maxsize=1)
def load_section_layout_contract() -> dict[str, Any]:
    with _SECTION_LAYOUT_CONTRACT_PATH.open('r', encoding='utf-8') as handle:
        raw = yaml.safe_load(handle) or {}
    sections = raw.get('sections') or {}
    if not sections:
        raise ValueError('Section layout contract missing sections.')
    return sections


CANONICAL_PRESET_NAMES: tuple[str, ...] = _load_preset_contract()['canonical_presets']
PRESET_ALIASES: dict[str, str] = _load_preset_contract()['aliases']
PRESET_NAMES = list(CANONICAL_PRESET_NAMES)
SLOT_TYPES = ["cannon", "armor", "generator", "core"]


def normalize_preset_name(value: str | None, *, allow_aliases: bool) -> str | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw in CANONICAL_PRESET_NAMES:
        return raw
    if allow_aliases:
        return PRESET_ALIASES.get(raw)
    return None


def require_canonical_preset_name(value: str | None, *, field_name: str) -> str:
    normalized = normalize_preset_name(value, allow_aliases=False)
    if normalized is None:
        raise ValueError(f'{field_name} must use a canonical preset name, got {value!r}.')
    return normalized


def build_runtime_state(ids_raw: IdsRaw, *, default_preset: str = "Farming", loadout_config: Optional[dict] = None, perk_config: Optional[dict] = None) -> AccountState:
    raw_sections = ids_raw.raw_sections
    labs = _parse_labs(raw_sections.get("Labs", []))
    workshop = _parse_workshop(raw_sections.get("WS", []))
    workshop_enhancements = _parse_table(raw_sections.get("WS+", []))
    workshop_enhancement_tracks = _parse_workshop_enhancements(raw_sections.get("WS+", []))
    ultimate_weapons, uw_tracks, uw_plus_tracks = _parse_uws(raw_sections.get("UWs", []))
    relics = _parse_relics(raw_sections.get("Relics", []))
    vault = _parse_vault(raw_sections.get("Vault", []))
    bots, bot_upgrades, bot_upgrade_tracks = _parse_bots(raw_sections.get("Bots", []))
    guardians = _parse_table(raw_sections.get("Guardians", []))
    guardian_tracks = _parse_guardians(raw_sections.get("Guardians", []))
    player_meta, tier_progression_waves, highest_tier_unlocked_number, highest_tier_unlocked_label = _parse_player_meta(raw_sections.get("Player & Stuff", []))
    theme_song_coin_multiplier = _parse_theme_song_coin_multiplier(raw_sections.get("Themes & Songs", []))
    cards_inventory, card_slots_unlocked, card_presets = _parse_cards(ids_raw.section_headers.get("Cards", []), raw_sections.get("Cards", []), labs)
    module_system_state, module_presets, modules_inventory = _parse_modules(raw_sections.get("Modules", []))
    _apply_loadout_overrides(loadout_config or {}, card_presets, module_presets)
    perk_presets, perk_preset_namespace_class, active_perk_preset = _parse_perk_config(perk_config or {})
    active_card_preset, active_module_preset = _resolve_active_loadout_presets(loadout_config or {}, default_preset)
    default_preset = require_canonical_preset_name(default_preset, field_name='default_preset')
    return AccountState(
        ids_path=ids_raw.ids_path,
        labs=labs,
        workshop=workshop,
        workshop_enhancements=workshop_enhancements,
        workshop_enhancement_tracks=workshop_enhancement_tracks,
        ultimate_weapons=ultimate_weapons,
        uw_tracks=uw_tracks,
        uw_plus_tracks=uw_plus_tracks,
        relics=relics,
        vault=vault,
        bots=bots,
        bot_upgrades=bot_upgrades,
        bot_upgrade_tracks=bot_upgrade_tracks,
        guardians=guardians,
        guardian_tracks=guardian_tracks,
        player_meta=player_meta,
        tier_progression_waves=tier_progression_waves,
        highest_tier_unlocked_number=highest_tier_unlocked_number,
        highest_tier_unlocked_label=highest_tier_unlocked_label,
        theme_song_coin_multiplier=theme_song_coin_multiplier,
        cards_inventory=cards_inventory,
        card_slots_unlocked=card_slots_unlocked,
        card_presets=card_presets,
        module_system_state=module_system_state,
        module_presets=module_presets,
        modules_inventory=modules_inventory,
        perk_presets=perk_presets,
        perk_preset_namespace_class=perk_preset_namespace_class,
        active_perk_preset=active_perk_preset,
        active_card_preset=active_card_preset,
        active_module_preset=active_module_preset,
        default_preset=default_preset,
        raw_sections=raw_sections,
    )


def _normalize_preset_name(value: str) -> Optional[str]:
    return normalize_preset_name(value, allow_aliases=True)


def _apply_loadout_overrides(loadout_config: Dict[str, object], card_presets: Dict[str, List[str]], module_presets: Dict[str, Dict[str, ModulePresetSelection]]) -> None:
    raw_card_presets = loadout_config.get('card_presets')
    if isinstance(raw_card_presets, dict):
        for preset_name, payload in raw_card_presets.items():
            if not isinstance(preset_name, str):
                continue
            normalized = _normalize_preset_name(preset_name)
            if normalized is None:
                raise ValueError(f"loadout_config.card_presets contains invalid preset name {preset_name!r}.")
            if isinstance(payload, list):
                cards = [str(item).strip() for item in payload if str(item).strip()]
                card_presets[normalized] = cards

    raw_module_presets = loadout_config.get('module_presets')
    if isinstance(raw_module_presets, dict):
        for preset_name, payload in raw_module_presets.items():
            if not isinstance(preset_name, str) or not isinstance(payload, dict):
                continue
            normalized = _normalize_preset_name(preset_name)
            if normalized is None:
                raise ValueError(f"loadout_config.module_presets contains invalid preset name {preset_name!r}.")
            for slot_type, selection in payload.items():
                if slot_type not in SLOT_TYPES or not isinstance(selection, dict):
                    continue
                current = module_presets.setdefault(normalized, {}).get(slot_type)
                if current is None:
                    current = ModulePresetSelection(primary=None, assist=None)
                primary = selection.get('primary')
                assist = selection.get('assist')
                module_presets[normalized][slot_type] = ModulePresetSelection(
                    primary=str(primary).strip() if primary is not None and str(primary).strip() else current.primary,
                    assist=str(assist).strip() if assist is not None and str(assist).strip() else current.assist,
                )



def _resolve_active_loadout_presets(loadout_config: Dict[str, object], default_preset: str) -> Tuple[str, str]:
    def _pick(key: str) -> str:
        raw = loadout_config.get(key)
        if raw is None:
            return default_preset
        if isinstance(raw, str):
            normalized = normalize_preset_name(raw, allow_aliases=False)
            if normalized is not None:
                return normalized
        if isinstance(raw, str) and not raw.strip():
            raise ValueError(f"{key} must not be empty when explicitly provided.")
        raise ValueError(f"{key} must use a canonical preset name, got {raw!r}.")

    return _pick('active_card_preset'), _pick('active_module_preset')


# ---------- generic helpers ----------

def _safe_cell(row: List[str], idx: int) -> str:
    return row[idx] if idx < len(row) else ""


def _optional_str(value: str) -> Optional[str]:
    value = value.strip()
    return value or None


def _parse_optional_int(value: str) -> Optional[int]:
    value = value.strip().replace(',', '')
    if value == '' or value == '?':
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _parse_optional_float(value: str) -> Optional[float]:
    value = value.strip().replace(',', '')
    if value == '' or value == '?':
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_bool(value: str) -> Optional[bool]:
    value = value.strip().lower()
    if value == 'true':
        return True
    if value == 'false':
        return False
    return None


def _row_has_data(row: List[str]) -> bool:
    return any(cell.strip() for cell in row)


# ---------- section parsers ----------

def _parse_labs(rows: List[List[str]]) -> Dict[str, Optional[int]]:
    out = {}
    for row in rows:
        name = _safe_cell(row, 0).strip()
        if name:
            out[name] = _parse_optional_int(_safe_cell(row, 1))
    return out


def _parse_workshop(rows: List[List[str]]) -> Dict[str, WorkshopEntrySnapshot]:
    out = {}
    # IDS chunk layout: label, farming_level, farming_cost, tourney_level, tourney_cost, testing_level, ... max
    workshop_layout = load_section_layout_contract()['workshop']
    level_cols = workshop_layout['preset_level_columns']
    value_cols = workshop_layout.get('preset_value_columns') or {}
    category_by_name = _category_registry_by_name(workshop_layout.get('category_registry') or {})
    for row in rows:
        name = _safe_cell(row, 0).strip()
        if not name or name == 'Workshop Upgrade':
            continue
        preset_levels = {preset: _parse_optional_int(_safe_cell(row, col)) for preset, col in level_cols.items()}
        preset_values = {preset: _parse_optional_float(_safe_cell(row, col)) for preset, col in value_cols.items()}
        out[name] = WorkshopEntrySnapshot(
            name=name,
            unlocked=None,
            preset_levels=preset_levels,
            preset_values=preset_values,
            max_level=_parse_optional_int(_safe_cell(row, load_section_layout_contract()['workshop']['max_level_column'])),
            category=category_by_name.get(name),
        )
    return out


def _parse_workshop_enhancements(rows: List[List[str]]) -> Dict[str, WorkshopEnhancementSnapshot]:
    out: Dict[str, WorkshopEnhancementSnapshot] = {}
    layout = load_section_layout_contract()['ws_plus']
    name_col = int(layout['name_column'])
    multiplier_col = int(layout['multiplier_column'])
    max_col = int(layout['max_level_column'])
    header_rows = int(layout['header_rows'])
    preset_cols: Dict[str, int] = {
        str(preset): int(col_idx) for preset, col_idx in layout['preset_level_columns'].items()
    }
    category_by_name = _category_registry_by_name(layout.get('category_registry') or {})
    for row in rows[header_rows:]:
        name = _safe_cell(row, name_col).strip()
        if not name:
            continue
        preset_levels = {preset: _parse_optional_int(_safe_cell(row, col_idx)) for preset, col_idx in preset_cols.items()}
        out[name] = WorkshopEnhancementSnapshot(
            name=name,
            current_multiplier=_parse_optional_float(_safe_cell(row, multiplier_col)),
            preset_levels=preset_levels,
            max_level=_parse_optional_int(_safe_cell(row, max_col)),
            category=category_by_name.get(name),
        )
    return out


def _category_registry_by_name(category_registry: Dict[str, List[str]]) -> Dict[str, str]:
    by_name: Dict[str, str] = {}
    for category, names in (category_registry or {}).items():
        for name in names or []:
            text = str(name).strip()
            if text:
                by_name[text] = str(category).strip().lower()
    return by_name


def _parse_table(rows: List[List[str]]) -> TableSnapshot:
    if not rows:
        return TableSnapshot(header=[], rows=[])
    header = [cell.strip() if cell.strip() else f'Column {i+1}' for i, cell in enumerate(rows[0])]
    body = []
    for row in rows[1:]:
        if _row_has_data(row):
            body.append([c.strip() for c in row])
    return TableSnapshot(header=header, rows=body)


def _iter_uw_blocks(rows: List[List[str]]) -> List[List[List[str]]]:
    uw_layout = load_section_layout_contract()['uw']
    block_size = int(uw_layout['block_size'])
    return [rows[i:i + block_size] for i in range(0, len(rows), block_size) if len(rows[i:i + block_size]) == block_size]


def _parse_uws(rows: List[List[str]]) -> Tuple[Dict[str, UltimateWeaponSnapshot], Dict[str, List[UwTrackSnapshot]], Dict[str, UwPlusTrackSnapshot]]:
    weapons = {}
    uw_tracks: Dict[str, List[UwTrackSnapshot]] = {}
    tracks = {}
    uw_layout = load_section_layout_contract()['uw']
    name_col = int(uw_layout['name_column'])
    attr_col = int(uw_layout['attribute_column'])
    resolved_col = int(uw_layout['resolved_value_column'])
    display_col = int(uw_layout['display_token_column'])
    stat_rows_per_block = int(uw_layout['stat_rows_per_block'])
    plus_row_index = int(uw_layout['plus_row_index'])
    for block in _iter_uw_blocks(rows):
        uw_name = _safe_cell(block[0], name_col).strip()
        if not uw_name:
            continue
        track_levels = []
        track_values = []
        for stat_row in block[:stat_rows_per_block]:
            token = _safe_cell(stat_row, display_col).strip()
            if token:
                track_levels.append(token.split('|', 1)[0].strip())
            raw_value = _parse_optional_float(_safe_cell(stat_row, resolved_col))
            track_values.append(raw_value)
            level = _parse_optional_int(token.split('|', 1)[0].strip()) if token else None
            track_name = _safe_cell(stat_row, attr_col).strip() or f'track_{len(uw_tracks.get(uw_name, [])) + 1}'
            uw_tracks.setdefault(uw_name, []).append(
                UwTrackSnapshot(
                    uw_name=uw_name,
                    track_name=track_name,
                    level=level,
                    level_token=token,
                    resolved_value=raw_value,
                )
            )
        weapons[uw_name] = UltimateWeaponSnapshot(name=uw_name, unlocked=_optional_str(_safe_cell(block[stat_rows_per_block - 1], name_col)), track_levels=track_levels, track_values=track_values)
        plus_track_name = _safe_cell(block[plus_row_index], attr_col).strip()
        if plus_track_name:
            key = f"{uw_name}::{plus_track_name}"
            tracks[key] = UwPlusTrackSnapshot(
                uw_name=uw_name,
                plus_track_name=plus_track_name,
                current_state=_safe_cell(block[plus_row_index], resolved_col).strip(),
                display_token=_safe_cell(block[plus_row_index], display_col).strip(),
            )
    return weapons, uw_tracks, tracks


def _parse_key_value_int(rows: List[List[str]]) -> Dict[str, Optional[int]]:
    return {row[0].strip(): _parse_optional_int(_safe_cell(row, 1)) for row in rows if _safe_cell(row, 0).strip()}


def _parse_key_value_scalar(rows: List[List[str]]) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for row in rows:
        key = _safe_cell(row, 0).strip()
        if not key:
            continue
        raw = _safe_cell(row, 1).strip()
        b = _parse_bool(raw)
        if b is not None:
            out[key] = b
            continue
        i = _parse_optional_int(raw)
        if i is not None:
            out[key] = i
            continue
        out[key] = _optional_str(raw)
    return out


def _parse_key_value_float(rows: List[List[str]]) -> Dict[str, Optional[float]]:
    return {row[0].strip(): _parse_optional_float(_safe_cell(row, 1)) for row in rows if _safe_cell(row, 0).strip()}


def _parse_relics(rows: List[List[str]]) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    for row in rows:
        key = _safe_cell(row, 0).strip()
        if not key:
            continue
        value = _parse_optional_float(_safe_cell(row, 1))
        if value is None:
            continue
        out[key] = value
    return out


def _parse_vault(rows: List[List[str]]) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for row in rows:
        key = _safe_cell(row, 0).strip()
        if not key or key == 'Total Bonuses':
            continue
        raw = _safe_cell(row, 1).strip()
        if not raw:
            continue
        b = _parse_bool(raw)
        if b is not None:
            out[key] = b
            continue
        i = _parse_optional_int(raw)
        if i is not None:
            out[key] = i
            continue
        out[key] = raw
    return out



def _parse_theme_song_coin_multiplier(rows: List[List[str]]) -> Optional[float]:
    for row in rows:
        raw = _safe_cell(row, 0).strip() or _safe_cell(row, 1).strip()
        if not raw:
            continue
        try:
            return float(raw)
        except ValueError:
            continue
    return None


def _extract_tier_number(tier_label: str) -> Optional[int]:
    match = re.match(r'^Tier\s+(\d+)$', tier_label.strip())
    if not match:
        return None
    return int(match.group(1))


def _parse_player_meta(rows: List[List[str]]) -> Tuple[Dict[str, Optional[str]], Dict[str, int], Optional[int], Optional[str]]:
    out: Dict[str, Optional[str]] = {}
    tier_progression_waves: Dict[str, int] = {}
    highest_tier_unlocked_number: Optional[int] = None
    for row in rows:
        left_key = _safe_cell(row, 0).strip()
        if left_key == 'Tier':
            tier_label = _safe_cell(row, 1).strip()
            tier_number = _extract_tier_number(tier_label)
            wave = _parse_optional_int(_safe_cell(row, 2))
            if tier_number is not None and wave is not None:
                tier_progression_waves[tier_label] = wave
                if wave > 0 and (highest_tier_unlocked_number is None or tier_number > highest_tier_unlocked_number):
                    highest_tier_unlocked_number = tier_number
        elif left_key:
            out[left_key] = _optional_str(_safe_cell(row, 1))
        right_key = _safe_cell(row, 4).strip()
        if right_key and right_key != 'Stat':
            out[right_key] = _optional_str(_safe_cell(row, 5))
    highest_tier_unlocked_label = f"Tier {highest_tier_unlocked_number}" if highest_tier_unlocked_number is not None else None
    return out, tier_progression_waves, highest_tier_unlocked_number, highest_tier_unlocked_label


def _parse_bots(rows: List[List[str]]) -> Tuple[List[str], Dict[str, Dict[str, int]], Dict[str, List[BotUpgradeSnapshot]]]:
    bot_layout = load_section_layout_contract()['bots']
    name_col = int(bot_layout['name_column'])
    attr_col = int(bot_layout['attribute_column'])
    resolved_col = int(bot_layout['resolved_value_column'])
    display_col = int(bot_layout['display_token_column'])
    truthy_tokens = {str(token).strip().lower() for token in bot_layout.get('truthy_name_tokens', [])}
    bots = []
    upgrades: Dict[str, Dict[str, int]] = {}
    typed_tracks: Dict[str, List[BotUpgradeSnapshot]] = {}
    current = None
    for row in rows:
        name = _safe_cell(row, name_col).strip()
        attr = _safe_cell(row, attr_col).strip()
        display = _safe_cell(row, display_col).strip()
        if name and name.lower() not in truthy_tokens:
            current = name
            if name not in bots:
                bots.append(name)
        if current and attr and display:
            level_token = display.split('|', 1)[0].strip()
            level = _parse_optional_int(level_token)
            resolved_value = _parse_optional_float(_safe_cell(row, resolved_col))
            resolved_unit = _extract_display_unit(display)
            if level is not None:
                upgrades.setdefault(current, {})[attr] = level
            typed_tracks.setdefault(current, []).append(
                BotUpgradeSnapshot(
                    bot_name=current,
                    track_name=attr,
                    level=level,
                    resolved_value=resolved_value,
                    resolved_unit=resolved_unit,
                )
            )
    return bots, upgrades, typed_tracks


def _extract_display_unit(display: str) -> Optional[str]:
    parts = [segment.strip() for segment in display.split('|')]
    if len(parts) < 2:
        return None
    value_token = parts[1]
    if not value_token:
        return None
    if value_token.startswith('x'):
        return 'x'
    if value_token.endswith('%'):
        return '%'
    if value_token.endswith('s'):
        return 's'
    if value_token.endswith('m'):
        return 'm'
    return None


def _parse_guardians(rows: List[List[str]]) -> Dict[str, List[GuardianTrackSnapshot]]:
    guardian_layout = load_section_layout_contract()['guardians']
    name_col = int(guardian_layout['name_column'])
    attr_col = int(guardian_layout['attribute_column'])
    resolved_col = int(guardian_layout['resolved_value_column'])
    display_col = int(guardian_layout['display_token_column'])
    truthy_tokens = {str(token).strip().lower() for token in guardian_layout.get('truthy_name_tokens', [])}
    current: Optional[str] = None
    tracks: Dict[str, List[GuardianTrackSnapshot]] = {}
    for row in rows:
        name = _safe_cell(row, name_col).strip()
        attr = _safe_cell(row, attr_col).strip()
        display = _safe_cell(row, display_col).strip()
        if name and name.lower() not in truthy_tokens:
            current = name
        if not current or not attr or not display:
            continue
        level_token = display.split('|', 1)[0].strip()
        level = _parse_optional_int(level_token)
        tracks.setdefault(current, []).append(
            GuardianTrackSnapshot(
                guardian_name=current,
                track_name=attr,
                level=level,
                resolved_value=_parse_optional_float(_safe_cell(row, resolved_col)),
                resolved_unit=_extract_display_unit(display),
            )
        )
    return tracks


def _parse_cards(section_header: List[str], rows: List[List[str]], labs: Dict[str, Optional[int]]) -> Tuple[Dict[str, CardSnapshot], Optional[int], Dict[str, List[str]]]:
    inventory: Dict[str, CardSnapshot] = {}
    presets: Dict[str, List[str]] = {preset: [] for preset in PRESET_NAMES}
    card_slots_unlocked: Optional[int] = _parse_optional_int(_safe_cell(section_header, 5))
    if not rows:
        return inventory, card_slots_unlocked, presets

    # IDS card blocks do not provide a separate tabular header row inside raw_sections['Cards'].
    # Each row is itself a card snapshot, while columns 3..7 are fixed preset assignment columns.
    # The first row often happens to contain the human preset labels in those assignment cells,
    # so we must not infer the schema from row 0 or skip it as a header.
    cards_contract = load_section_layout_contract()['cards']
    preset_columns: Dict[int, str] = {
        int(column_index): str(preset_name)
        for preset_name, column_index in cards_contract['preset_assignment_columns'].items()
    }
    preset_label_tokens = set(cards_contract['label_tokens'])

    for row in rows:
        name = _safe_cell(row, 0).strip()
        if not name:
            continue
        level = _parse_optional_int(_safe_cell(row, 1))
        if level is not None:
            inventory[name] = CardSnapshot(
                name=name,
                level=level,
                mastery_unlocked=_parse_bool(_safe_cell(row, 2)),
                mastery_lab_level=labs.get(f"{name} Mastery"),
            )
        for idx, preset_name in preset_columns.items():
            card_name = _safe_cell(row, idx).strip()
            if not card_name or card_name in preset_label_tokens:
                continue
            presets[preset_name].append(card_name)
    return inventory, card_slots_unlocked, presets


def _extract_slot_chunk(row: List[str], slot_index: int) -> List[str]:
    # The IDS module block uses four repeated chunks with irregular tail width on the core slot.
    starts = [0, 5, 10, 15]
    ends = [5, 10, 15, len(row)]
    start = starts[slot_index]
    end = ends[slot_index]
    chunk = row[start:end]
    while len(chunk) < 5:
        chunk.append('')
    return chunk


def _parse_modules(rows: List[List[str]]) -> Tuple[Dict[str, ModuleSystemState], Dict[str, Dict[str, ModulePresetSelection]], Dict[str, ModuleSnapshot]]:
    system_state: Dict[str, ModuleSystemState] = {}
    presets: Dict[str, Dict[str, ModulePresetSelection]] = {preset: {} for preset in PRESET_NAMES}
    inventory: Dict[str, ModuleSnapshot] = {}
    label_map = load_section_layout_contract()['modules']['preset_label_aliases']
    for slot_index, slot_type in enumerate(SLOT_TYPES):
        slot_rows = [_extract_slot_chunk(row, slot_index) for row in rows]
        assist = None
        assist_level = None
        rarity_cap = None
        multiplier_cap = None
        substat_cap = None
        preset_map = {preset: ModulePresetSelection(primary=None, assist=None) for preset in PRESET_NAMES}

        # system rows
        if slot_rows:
            assist = _parse_bool(_safe_cell(slot_rows[0], 1))
            assist_level = _parse_optional_int(_safe_cell(slot_rows[0], 2))
        if len(slot_rows) > 1:
            rarity_cap = _optional_str(_safe_cell(slot_rows[1], 1))
        if len(slot_rows) > 2:
            multiplier_cap = _parse_optional_float(_safe_cell(slot_rows[2], 1))
        if len(slot_rows) > 3:
            substat_cap = _parse_optional_float(_safe_cell(slot_rows[3], 1))

        # preset rows 5..15
        idx = 5
        current_preset = None
        while idx < min(len(slot_rows), 16):
            row = slot_rows[idx]
            label = _safe_cell(row, 0).strip()
            if label in label_map:
                current_preset = label_map[label]
                idx += 1
                continue
            if current_preset and label == 'Primary Slot':
                preset_map[current_preset] = replace(preset_map[current_preset], primary=_optional_str(_safe_cell(row, 1)))
            elif current_preset and label == 'Assist Slot':
                preset_map[current_preset] = replace(preset_map[current_preset], assist=_optional_str(_safe_cell(row, 1)))
            idx += 1

        # inventory blocks from row 16 onward: name, header, values, then substat rows until next module name
        idx = 16
        while idx < len(slot_rows):
            name = _safe_cell(slot_rows[idx], 0).strip()
            if not name:
                idx += 1
                continue
            if idx + 2 >= len(slot_rows):
                break
            header_row = slot_rows[idx + 1]
            value_row = slot_rows[idx + 2]
            if _safe_cell(header_row, 0).strip() != 'Rarity' or _safe_cell(header_row, 1).strip() != 'Level':
                idx += 1
                continue
            mod = ModuleSnapshot(
                name=name,
                slot_type=slot_type,
                rarity=_optional_str(_safe_cell(value_row, 0)),
                level=_parse_optional_int(_safe_cell(value_row, 1)),
                stat=_optional_str(_safe_cell(value_row, 2)),
                substats=[],
            )
            j = idx + 3
            while j < len(slot_rows):
                sub = slot_rows[j]
                label = _safe_cell(sub, 0).strip()
                if label and j + 2 < len(slot_rows) and _safe_cell(slot_rows[j + 1], 0).strip() == 'Rarity' and _safe_cell(slot_rows[j + 1], 1).strip() == 'Level':
                    break
                if label:
                    mod.substats.append(
                        ModuleSubstat(
                            name=label,
                            value=_optional_str(_safe_cell(sub, 2)) or _optional_str(_safe_cell(sub, 3)),
                            raw_token=_optional_str(_safe_cell(sub, 3)),
                        )
                    )
                j += 1
            inventory[name] = mod
            idx = j

        system_state[slot_type] = ModuleSystemState(
            slot_type=slot_type,
            assist_unlocked=assist,
            assist_level=assist_level,
            rarity_cap=rarity_cap,
            multiplier_cap=multiplier_cap,
            substat_cap=substat_cap,
        )
        for preset_name in PRESET_NAMES:
            presets[preset_name][slot_type] = preset_map[preset_name]
    return system_state, presets, inventory


def _parse_perk_config(loadout_config: Dict[str, object]) -> Tuple[Dict[str, List[PerkSelection]], str, Optional[str]]:
    raw_presets = loadout_config.get('perk_presets')
    active_perk_preset = loadout_config.get('active_perk_preset')
    preset_namespace_class = str(loadout_config.get('preset_namespace_class') or '').strip().lower()
    raw_banned = loadout_config.get('banned_perk_ids')
    banned_perk_ids = {
        str(item).strip()
        for item in (raw_banned if isinstance(raw_banned, list) else [])
        if str(item).strip()
    }
    out: Dict[str, List[PerkSelection]] = {}
    if not isinstance(raw_presets, dict):
        active = active_perk_preset.strip() if isinstance(active_perk_preset, str) and active_perk_preset.strip() else None
        if active and normalize_preset_name(active, allow_aliases=False) is None and preset_namespace_class != 'transient':
            raise ValueError(f"active_perk_preset must use a canonical preset name in canonical flows, got {active!r}.")
        return out, (preset_namespace_class or 'canonical'), active

    def _normalize_single(item) -> Optional[PerkSelection]:
        if isinstance(item, str) and item.strip():
            return PerkSelection(perk_id=item.strip(), picks=1)
        if isinstance(item, dict):
            perk_id = str(item.get('perk_id', '')).strip()
            if not perk_id:
                return None
            try:
                picks = int(item.get('picks', 1))
            except (TypeError, ValueError):
                picks = 1
            return PerkSelection(perk_id=perk_id, picks=max(0, picks))
        return None

    for preset_name, payload in raw_presets.items():
        if not isinstance(preset_name, str) or not preset_name.strip():
            continue
        preset_name = preset_name.strip()
        selections: List[PerkSelection] = []
        if isinstance(payload, list):
            for item in payload:
                parsed = _normalize_single(item)
                if parsed is not None and parsed.perk_id not in banned_perk_ids:
                    selections.append(parsed)
        elif isinstance(payload, dict):
            for perk_id, picks_raw in payload.items():
                if not isinstance(perk_id, str) or not perk_id.strip():
                    continue
                try:
                    picks = int(picks_raw)
                except (TypeError, ValueError):
                    picks = 1
                normalized_perk_id = perk_id.strip()
                if normalized_perk_id in banned_perk_ids:
                    continue
                selections.append(PerkSelection(perk_id=normalized_perk_id, picks=max(0, picks)))
        normalized_preset_name = normalize_preset_name(preset_name, allow_aliases=False)
        if normalized_preset_name is None:
            if preset_namespace_class != 'transient':
                raise ValueError(
                    f"perk_presets contains non-canonical preset name {preset_name!r}; "
                    "canonical flows must use canonical preset names only."
                )
            out[preset_name] = selections
            continue
        out[normalized_preset_name] = selections

    active = active_perk_preset.strip() if isinstance(active_perk_preset, str) and active_perk_preset.strip() else None
    if active and normalize_preset_name(active, allow_aliases=False) is None and preset_namespace_class != 'transient':
        raise ValueError(f"active_perk_preset must use a canonical preset name in canonical flows, got {active!r}.")
    return out, (preset_namespace_class or 'canonical'), active
