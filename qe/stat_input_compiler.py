from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from qe.query_module_policy import (
    load_assist_efficiency_lookup,
    load_module_substat_values,
    load_module_unique_effect_values,
    module_main_effect_multiplier,
    normalize_module_unique_rarity,
)
from qe.query_perk_compiler import (
    TRADE_OFF_BENEFIT_EFFECT_INDEXES,
    TRADE_OFF_LAB_SCALED_BENEFIT_EFFECT_INDEXES,
    active_perk_selections as _active_perk_selections,
    normalized_multiplier as _normalized_multiplier,
    perk_lab_state as _perk_lab_state,
    perk_value_from_effect as _perk_value_from_effect,
    perk_value_type_for_operation as _perk_value_type_for_operation,
    scaled_perk_value as _scaled_perk_value,
)
from qe.query_routing import (
    ACCOUNT_METADATA_ROWS,
    CAPABILITY_POLICY_ROWS,
    CARD_NAME_FALLBACK_DESTINATION,
    CARD_TARGET_SURFACE_TO_DESTINATION,
    ENHANCEMENT_ALIAS_OVERRIDES,
    GOVERNED_NUMERIC_ROWS,
    GUARDIAN_DESTINATION_OVERRIDES,
    LAB_APPLICATION_TARGET_TO_DESTINATION,
    LAB_FORMULA_VALUES,
    LAB_IDS_TO_CONTRIBUTOR,
    MODULE_SUBSTAT_NAME_TO_DESTINATION,
    PARSER_DROP_ROWS,
    PERK_TARGET_DESTINATION_OVERRIDES,
    RELIC_ALIAS_OVERRIDES,
    RELIC_CONTRIBUTOR_OVERRIDES,
    UW_CONTRIBUTOR_OVERRIDES,
    UW_MECHANIC_DESTINATION_OVERRIDES,
    VAULT_BOOLEAN_FLAGS,
    VAULT_NUMERIC_OVERRIDES,
    WORKSHOP_FORMULA_VALUES,
    WORKSHOP_IDS_TO_CONTRIBUTOR,
    _UW_LAB_DIRECT_DESTINATION,
    bind_alias_destination,
    bind_destination,
    bind_kb_fields,
    bind_perk_effect_destination,
    compiler_routing_indexes,
    load_card_effect_targets,
    load_lab_application_registry,
    load_theme_song_registry,
    mapping_lookup_for_family_name,
    slug_text,
    uw_contributor_id,
)
from qe.query_state_mode_policy import (
    SUPPORTED_STATE_MODES,
    normalize_state_mode,
    row_in_state_mode,
    state_mode_support,
    supported_state_modes,
)
from input.state_types import AccountState, ScenarioProjectionState, projection_state_for_mode
from qe.models import bind_preset_family
from qe.contracts import sanitize_preset_name_for_canonical_output
from qe.models import StatInput

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / 'kb'
KB_TABLES = KB / 'global-rules' / 'tables'


def _set_row_field(row: StatInput, field_name: str, value) -> None:
    object.__setattr__(row, field_name, value)


def _canonical_module_rarity_label(value: object) -> str | None:
    rarity = str(value or '').strip().lower()
    if not rarity:
        return None
    if rarity.startswith('ancestral'):
        return 'Ancestral'
    if rarity.startswith('mythic'):
        return 'Mythic'
    if rarity.startswith('legendary'):
        return 'Legendary'
    if rarity.startswith('epic'):
        return 'Epic'
    if rarity.startswith('rare'):
        return 'Rare'
    if rarity.startswith('common'):
        return 'Common'
    return str(value).strip().title()


def _module_substat_lookup_name(value: object) -> str:
    name = str(value or '').strip()
    if name == 'Defense %':
        return 'Defense'
    if name == 'Critical Factor':
        return 'Crit Factor'
    if name == 'MultiShot Chance':
        return 'Multishot Chance'
    return name

LAB_VALUES_PATH = KB / 'labs' / 'tables' / 'lab-values.csv'
WORKSHOP_VALUES_PATH = KB / 'workshop' / 'tables' / 'workshop-values.csv'
WORKSHOP_VALUES_DERIVED_PATH = KB / 'workshop' / 'derived' / 'materialized' / 'workshop-values.csv'
CARD_LADDERS_PATH = KB / 'cards' / 'tables' / 'card-base-ladders.csv'
CARD_MASTERIES_PATH = KB / 'cards' / 'tables' / 'card-masteries.csv'
CARD_EFFECT_REGISTRY_PATH = KB / 'cards' / 'tables' / 'card-effect-registry.csv'
MODULE_SUBSTATS_TABLE_PATH = KB / 'modules' / 'tables' / 'module-substats.csv'
ASSIST_MODULE_BONUS_VALUES_PATH = KB / 'modules' / 'tables' / 'assist-module-bonus-efficiency-wiki-truth.csv'
ASSIST_MODULE_SUBSTAT_VALUES_PATH = KB / 'modules' / 'tables' / 'assist-module-substats-efficiency-wiki-truth.csv'
MODULE_COIN_COST_VALUES_PATH = KB / 'modules' / 'tables' / 'module-coin-cost-wiki-truth.csv'
MODULE_SHARD_COST_VALUES_PATH = KB / 'modules' / 'tables' / 'module-shard-cost-wiki-truth.csv'
STARTING_CASH_VALUES_PATH = KB / 'labs' / 'tables' / 'starting-cash-wiki-truth.csv'
BOT_TRACK_REGISTRY_PATH = KB / 'bots' / 'tables' / 'bot-track-registry.csv'
BOT_TRACK_VALUES_PATH = KB / 'bots' / 'tables' / 'bot-upgrade-tracks-long.csv'
BOT_LABS_SUMMARY_PATH = KB / 'bots' / 'tables' / 'bot-labs-summary.yaml'
GUARDIAN_TRACK_REGISTRY_PATH = KB / 'guardians' / 'tables' / 'guardian-track-registry.csv'
UW_TRACK_REGISTRY_PATH = KB / 'ultimate-weapons' / 'tables' / 'uw-track-registry.csv'
UW_TRACK_VALUES_PATH = KB / 'ultimate-weapons' / 'tables' / 'ultimate-weapon-track-ladders.csv'
UW_PLUS_VALUES_PATH = KB / 'ultimate-weapons' / 'tables' / 'ultimate-weapon-plus-ladders.csv'
THEME_SONG_REGISTRY_PATH = KB_TABLES / 'theme-song-input-registry.csv'
PERK_ENTITY_REGISTRY_PATH = KB / 'perks' / 'tables' / 'perk-entity-registry.csv'
PERK_EFFECT_REGISTRY_PATH = KB / 'perks' / 'tables' / 'perk-effect-registry.csv'

SCOUT_GUARDIAN_TABLE_PATH = KB / 'guardians' / 'tables' / 'wiki-verified-guardian-scout-upgrades.csv'

# ── UW lab wiki-verified value tables (from UW complete branch) ──
_UW_LAB_TABLE_REGISTRY: Dict[str, Tuple[str, str]] = {
    'Lightning Amplifier - Scatter': ('ultimate-weapons/tables/wiki-verified-lightning-amplifier-scatter.csv', 'value'),
    'Swamp Radius': ('ultimate-weapons/tables/wiki-verified-swamp-radius.csv', 'value'),
    'Swamp Stun Chance': ('ultimate-weapons/tables/wiki-verified-swamp-stun-chance.csv', 'value'),
    'Swamp Stun Time': ('ultimate-weapons/tables/wiki-verified-swamp-stun-time.csv', 'value'),
    'Missile Barrage Quantity': ('ultimate-weapons/tables/wiki-verified-missile-barrage-quantity.csv', 'value'),
    'Missile Radius': ('ultimate-weapons/tables/wiki-verified-missiles-radius.csv', 'value'),
    'Inner Mine Blast Radius': ('ultimate-weapons/tables/wiki-verified-inner-mine-blast-radius.csv', 'value'),
    'Inner Mine Rotation Speed': ('ultimate-weapons/tables/wiki-verified-inner-mine-rotation-speed.csv', 'value'),
    'Recharge Missile Barrage': ('ultimate-weapons/tables/wiki-verified-recharge-missile-barrage.csv', 'value'),
    'Inner Land Mine - Chrono Jump': ('ultimate-weapons/tables/wiki-verified-inner-land-mine-chrono-jump.csv', 'value'),
    'Swamp Rend - Additional Enemies': ('ultimate-weapons/tables/wiki-verified-swamp-rend-additional-enemies.csv', 'value'),
}

@lru_cache(maxsize=1)
def _load_lab_values() -> Dict[Tuple[str, int], float]:
    out: Dict[Tuple[str, int], float] = {}
    with LAB_VALUES_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                name = str(row['lab_primary_name']).strip()
                level = int(row['level'])
                value = float(row['value'])
            except (ValueError, TypeError):
                continue
            out[(name, level)] = value
            out[(slug_text(name), level)] = value
    return out



@lru_cache(maxsize=1)
def _load_lab_summary_lookup() -> Dict[str, Dict[str, float | str]]:
    path = KB / 'labs' / 'tables' / 'lab-track-summary.csv'
    if not path.exists():
        return {}
    out: Dict[str, Dict[str, float | str]] = {}
    with path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            name = str(row.get('lab_primary_name', '')).strip()
            try:
                payload = {
                    'level_min': float(row.get('level_min', 0)),
                    'level_max': float(row.get('level_max', 0)),
                    'value_min': float(row.get('value_min', 0)),
                    'linear_step': float(row.get('linear_step', 0)),
                    'formula_family': str(row.get('formula_family', '')).strip().lower(),
                }
            except (TypeError, ValueError):
                continue
            out[name] = payload
            out[slug_text(name)] = payload
    return out


def _lab_value_with_fallback(name: str, level: int | None, lab_values: Dict[Tuple[str, int], float], lab_summary: Dict[str, Dict[str, float | str]]) -> float | None:
    if level is None:
        return None
    direct = lab_values.get((name, level))
    if direct is None:
        direct = lab_values.get((slug_text(name), level))
    if direct is not None:
        return direct
    if name in LAB_FORMULA_VALUES:
        try:
            return LAB_FORMULA_VALUES[name](level)
        except Exception:
            return None
    summary = lab_summary.get(name) or lab_summary.get(slug_text(name))
    if not summary:
        return None
    if str(summary.get('formula_family', '')).lower() != 'linear':
        return None
    try:
        level_min = int(float(summary.get('level_min', 1)))
        value_min = float(summary.get('value_min', 0.0))
        linear_step = float(summary.get('linear_step', 0.0))
        return value_min + (level - level_min) * linear_step
    except (TypeError, ValueError):
        return None

@lru_cache(maxsize=1)
def _load_workshop_value_lookup() -> Dict[Tuple[str, int], float]:
    out: Dict[Tuple[str, int], float] = {}
    # Prefer the derived materialized table because it contains the full workshop ladders
    # for the published core stats. The older flat table in kb/workshop/tables tops out at
    # low levels and silently causes the engine to fall back to raw level numbers.
    with WORKSHOP_VALUES_DERIVED_PATH.open(newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        pairs = []
        for i in range(0, len(header), 2):
            if i + 1 < len(header) and header[i+1]:
                pairs.append((i, header[i+1]))
        normalized = {'HPregen': 'Health Regen'}
        for row in reader:
            for i, col in pairs:
                if i + 1 >= len(row):
                    continue
                try:
                    level = int(float(row[i]))
                    value = float(row[i+1])
                except (ValueError, TypeError):
                    continue
                ids_name = normalized.get(col, col)
                out[(ids_name, level)] = value
    # Keep the old direct table as a fallback only.
    if WORKSHOP_VALUES_PATH.exists():
        pairs = [
            ('Level', 'Damage', 'Damage'),
            ('Level.1', 'Health', 'Health'),
            ('Level.2', 'HPregen', 'Health Regen'),
            ('Level.3', 'DefAbs', 'Defense Absolute'),
            ('Level.4', 'Damage / Meter', 'Damage / Meter'),
            ('Level.5', 'Lifesteal', 'Lifesteal'),
        ]
        with WORKSHOP_VALUES_PATH.open(newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                for level_col, value_col, ids_name in pairs:
                    raw_level = row.get(level_col)
                    raw_value = row.get(value_col)
                    if raw_level in (None, '') or raw_value in (None, ''):
                        continue
                    try:
                        level = int(float(raw_level))
                        value = float(raw_value)
                    except (ValueError, TypeError):
                        continue
                    if (ids_name, level) not in out:
                        out[(ids_name, level)] = value
    return out


@lru_cache(maxsize=1)
def _load_card_ladders() -> Dict[Tuple[str, int], Dict[str, str]]:
    out: Dict[Tuple[str, int], Dict[str, str]] = {}
    with CARD_LADDERS_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                out[(row['canonical_name'], int(row['base_level']))] = row
            except (ValueError, TypeError):
                continue

    cards_cache_dir = KB / 'cards' / 'sources' / 'raw' / 'repo-cache' / 'wiki'
    for path in sorted(cards_cache_dir.glob('cards-*.csv')):
        with path.open(newline='') as f:
            rows = list(csv.reader(f))
        if not rows:
            continue
        header = rows[0]
        level_columns = [(idx, cell) for idx, cell in enumerate(header) if str(cell).strip().lower().startswith('lv.')]
        for row in rows[1:]:
            if len(row) < 3:
                continue
            canonical_name = str(row[1]).strip()
            if not canonical_name:
                continue
            for idx, cell in level_columns:
                if idx >= len(row):
                    continue
                raw = str(row[idx]).strip()
                if not raw:
                    continue
                try:
                    level = int(str(cell).replace('Lv.', '').strip())
                except (TypeError, ValueError):
                    continue
                key = (canonical_name, level)
                if key in out:
                    continue
                cleaned = raw.replace('%', '').replace('x', '').replace('?', '').strip()
                if cleaned.startswith('.'):
                    cleaned = '0' + cleaned
                try:
                    float(cleaned)
                except ValueError:
                    continue
                out[key] = {
                    'card_id': slug_text(canonical_name).replace(' ', '_').upper(),
                    'canonical_name': canonical_name,
                    'base_level': str(level),
                    'raw_value': cleaned,
                    'unit': 'percent' if '%' in raw else 'raw_number',
                    'source_surface': str(path),
                    'source_url': 'https://the-tower-idle-tower-defense.fandom.com/wiki/Cards',
                    'verification_status': 'bundled_raw_wiki_cache_fallback',
                }
    return out


@lru_cache(maxsize=1)
def _load_bot_track_values() -> Dict[Tuple[str, str, int], float]:
    out: Dict[Tuple[str, str, int], float] = {}
    with BOT_TRACK_VALUES_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                out[(row['bot_name'], row['track_name'], int(row['level']))] = float(row['track_value'])
            except (ValueError, TypeError):
                continue
    return out


@lru_cache(maxsize=1)
def _load_bot_lab_rules() -> Dict[str, Dict[str, float | str]]:
    data = yaml.safe_load(BOT_LABS_SUMMARY_PATH.read_text(encoding='utf-8')) or {}
    out: Dict[str, Dict[str, float | str]] = {}
    for key, payload in (data.get('bot_labs') or {}).items():
        out[key] = payload or {}
    return out


BOT_UPGRADE_BINDINGS = {
    ('Golden Bot', 'Duration'): ('bot_upgrade__golden_bot__duration__seconds', 'duration_seconds'),
    ('Golden Bot', 'Cooldown'): ('bot_upgrade__golden_bot__cooldown__seconds', 'cooldown_seconds'),
    ('Golden Bot', 'Bonus'): ('bot_upgrade__golden_bot__bonus__multiplier', 'bonus_multiplier_x'),
    ('Golden Bot', 'Range'): ('bot_upgrade__golden_bot__range__m', 'range_meters'),
    ('Amplify Bot', 'Duration'): ('bot_upgrade__amplify_bot__duration__seconds', 'duration_seconds'),
    ('Amplify Bot', 'Cooldown'): ('bot_upgrade__amplify_bot__cooldown__seconds', 'cooldown_seconds'),
    ('Amplify Bot', 'Bonus'): ('bot_upgrade__amplify_bot__bonus__multiplier', 'bonus_multiplier_x'),
    ('Amplify Bot', 'Range'): ('bot_upgrade__amplify_bot__range__m', 'range_meters'),
    ('Flame Bot', 'Cooldown'): ('bot_upgrade__flame_bot__cooldown__seconds', 'cooldown_seconds'),
    ('Flame Bot', 'Damage'): ('bot_upgrade__flame_bot__damage__multiplier', 'damage_multiplier_x'),
    ('Flame Bot', 'Damage R.'): ('bot_upgrade__flame_bot__damage_reduction__pct', 'damage_reduction_pct'),
    ('Flame Bot', 'Range'): ('bot_upgrade__flame_bot__range__m', 'range_meters'),
    ('Thunder Bot', 'Duration'): ('bot_upgrade__thunder_bot__duration__seconds', 'duration_seconds'),
    ('Thunder Bot', 'Cooldown'): ('bot_upgrade__thunder_bot__cooldown__seconds', 'cooldown_seconds'),
    ('Thunder Bot', 'Range'): ('bot_upgrade__thunder_bot__range__m', 'range_meters'),
    ('Thunder Bot', 'Linger'): ('bot_upgrade__thunder_bot__linger_slow__pct', 'linger_seconds'),
}

BOT_RANGE_CANONICALS = [
    ('mechanic_param', 'bot.global.range_bonus_m'),
    ('mechanic_param', 'bot.golden.range_m'),
    ('mechanic_param', 'bot.amplify.range_m'),
    ('mechanic_param', 'bot.flame.range_m'),
    ('mechanic_param', 'bot.thunder.range_m'),
]

BOT_LAB_BINDINGS = {
    'Amp Bot - Cooldown': ('amplify_bot_cooldown', -1.0),
    'Amp Bot - Duration': ('amplify_bot_duration', 0.5),
    'Flame Bot - Cooldown': ('flame_bot_cooldown', -1.0),
    'Gold Bot - Cooldown': ('golden_bot_cooldown', -1.0),
    'Gold Bot - Duration': ('golden_bot_duration', 0.5),
    'Thunder Bot - Cooldown': ('thunder_bot_cooldown', -1.0),
    'Thunder Bot - Linger Time': ('thunder_bot_linger_time', 0.5),
}


@lru_cache(maxsize=1)
def _load_guardian_track_values() -> Dict[Tuple[str, str, int], float]:
    out: Dict[Tuple[str, str, int], float] = {}
    with GUARDIAN_TRACK_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                out[(row['guardian_name'], row['track_attribute'], int(row['level']))] = float(row['value'])
            except (ValueError, TypeError):
                continue
    return out


@lru_cache(maxsize=1)
def _load_uw_track_values() -> Dict[Tuple[str, str, int], float]:
    out: Dict[Tuple[str, str, int], float] = {}
    with UW_TRACK_VALUES_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                out[(row['uw_name'], row['track_name'], int(row['level_index']))] = float(row['value'])
            except (ValueError, TypeError):
                continue
    return out


@lru_cache(maxsize=1)
def _load_uw_track_order() -> Dict[str, List[str]]:
    """Return {canonical_uw_name: [track_name, ...]} from the UW track registry."""
    out: Dict[str, List[str]] = {}
    with UW_TRACK_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            name = row.get('canonical_name', '').strip()
            track = row.get('track_name', '').strip()
            if name and track:
                out.setdefault(name, [])
                if track not in out[name]:
                    out[name].append(track)
    return out




@lru_cache(maxsize=1)
def _load_uw_plus_values() -> Dict[Tuple[str, str, int], float]:
    out: Dict[Tuple[str, str, int], float] = {}
    with UW_PLUS_VALUES_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            try:
                out[(row['uw_name'], row['plus_track_name'], int(row['level_index']))] = float(row['value'])
            except (ValueError, TypeError):
                continue
    return out


@lru_cache(maxsize=1)
def _load_uw_lab_wiki_values() -> Dict[Tuple[str, int], float]:
    """Load all wiki-verified UW lab value tables into a unified (lab_name, level) -> value lookup."""
    out: Dict[Tuple[str, int], float] = {}
    for lab_name, (rel_path, value_col) in _UW_LAB_TABLE_REGISTRY.items():
        path = KB / rel_path
        if not path.exists():
            continue
        with path.open(newline='') as f:
            for row in csv.DictReader(f):
                try:
                    level = int(row['level'])
                    raw = str(row[value_col]).strip().replace('%', '').replace('x', '').replace('X', '').replace('#', '').replace('+', '')
                    if raw:
                        out[(lab_name, level)] = float(raw)
                except (ValueError, TypeError, KeyError):
                    continue
    return out


@lru_cache(maxsize=1)
def _load_guardian_scout_values() -> Dict[Tuple[str, int], float]:
    out: Dict[Tuple[str, int], float] = {}
    with SCOUT_GUARDIAN_TABLE_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            level = int(row['level'])
            for key, col in [('Cooldown','cooldown_seconds'),('Range Bonus','range_bonus_multiplier'),('Duration','duration_seconds')]:
                try:
                    val = float(row[col])
                except (ValueError, TypeError):
                    continue
                out[(key, level)] = val
    return out



def _load_level_value_table(path: Path, value_column: str) -> Dict[int, float]:
    out: Dict[int, float] = {}
    if not path.exists():
        return out
    with path.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            try:
                out[int(row['level'])] = float(row[value_column])
            except (KeyError, TypeError, ValueError):
                continue
    return out


@lru_cache(maxsize=1)
def _load_assist_module_bonus_values() -> Dict[int, float]:
    return _load_level_value_table(ASSIST_MODULE_BONUS_VALUES_PATH, 'value_pct')


@lru_cache(maxsize=1)
def _load_assist_module_substat_values() -> Dict[int, float]:
    return _load_level_value_table(ASSIST_MODULE_SUBSTAT_VALUES_PATH, 'value_pct')


@lru_cache(maxsize=1)
def _load_module_coin_cost_values() -> Dict[int, float]:
    return _load_level_value_table(MODULE_COIN_COST_VALUES_PATH, 'value_pct')


@lru_cache(maxsize=1)
def _load_module_shard_cost_values() -> Dict[int, float]:
    return _load_level_value_table(MODULE_SHARD_COST_VALUES_PATH, 'value_pct')


@lru_cache(maxsize=1)
def _load_starting_cash_values() -> Dict[int, float]:
    return _load_level_value_table(STARTING_CASH_VALUES_PATH, 'value_cash')


ACCOUNT_METADATA_DESTINATIONS: Dict[str, Tuple[str, str]] = {
    'Buy Multiplier': ('meta_progression_param', 'account_meta.buy_multiplier'),
    'Card Presets': ('account_flag', 'account_meta.card_presets'),
    'More Round Stats': ('account_flag', 'account_meta.more_round_stats'),
    'Workshop Respec': ('account_flag', 'account_meta.workshop_respec'),
    'Reroll Daily Mission': ('account_flag', 'account_meta.reroll_daily_mission'),
    'Event Relics': ('meta_progression_param', 'account_meta.event_relic_count'),
    'Guild Relics': ('meta_progression_param', 'account_meta.guild_relic_count'),
    'Other Relics': ('meta_progression_param', 'account_meta.other_relic_count'),
    'Total Relics': ('meta_progression_param', 'account_meta.total_relic_count'),
    'Keys spent': ('meta_progression_param', 'account_meta.keys_spent'),
}

CAPABILITY_POLICY_DESTINATIONS: Dict[str, Tuple[str, str]] = {
    'Unlock Perks': ('capability', 'capability.perks.unlock'),
    'Auto Pick Perks': ('capability', 'capability.perks.auto_pick'),
    'Perk Option Quantity': ('capability', 'capability.perks.option_quantity'),
    'First Perk Choice': ('capability', 'capability.perks.first_choice'),
    'Ban Perks': ('capability', 'capability.perks.ban_count'),
    'Auto Pick Ranking': ('capability', 'capability.perks.auto_pick_ranking'),
    'Target Priority': ('capability', 'capability.target_priority'),
    'Extra Orb Adjuster': ('capability', 'capability.extra_orb_adjuster'),
    'Unmerge Module': ('capability', 'capability.modules.unmerge'),
    'Armor Effect Bans': ('capability', 'capability.modules.effect_bans.armor'),
    'Cannon Effect Bans': ('capability', 'capability.modules.effect_bans.cannon'),
    'Core Effect Bans': ('capability', 'capability.modules.effect_bans.core'),
    'Generator Effect Bans': ('capability', 'capability.modules.effect_bans.generator'),
}

_BOOLEAN_ACCOUNT_METADATA_ROWS = {
    'Card Presets',
    'More Round Stats',
    'Workshop Respec',
    'Reroll Daily Mission',
}

_BOOLEAN_CAPABILITY_POLICY_ROWS = {
    'Unlock Perks',
    'Auto Pick Perks',
    'Unmerge Module',
}

_TEXT_CAPABILITY_POLICY_ROWS = {
    'Auto Pick Ranking',
    'Target Priority',
    'First Perk Choice',
}

_ASSIST_BONUS_DESTINATIONS = {
    'Armor': ('mechanic_param', 'module.armor.assist_lab_bonus_pct'),
    'Cannon': ('mechanic_param', 'module.cannon.assist_lab_bonus_pct'),
    'Core': ('mechanic_param', 'module.core.assist_lab_bonus_pct'),
    'Generator': ('mechanic_param', 'module.generator.assist_lab_bonus_pct'),
}

_ASSIST_SUBSTAT_DESTINATIONS = {
    'Armor': ('mechanic_param', 'module.armor.assist_substat_lab_bonus_pct'),
    'Cannon': ('mechanic_param', 'module.cannon.assist_substat_lab_bonus_pct'),
    'Core': ('mechanic_param', 'module.core.assist_substat_lab_bonus_pct'),
    'Generator': ('mechanic_param', 'module.generator.assist_substat_lab_bonus_pct'),
}

_ULTIMATE_DESTINATIONS = {
    "Basic's Ultimate": ('environment_param', 'enemy.basic.ultimate_enabled'),
    "Boss's Ultimate": ('environment_param', 'enemy.boss.ultimate_enabled'),
    "Fast's Ultimate": ('environment_param', 'enemy.fast.ultimate_enabled'),
    "Protector's Ultimate": ('environment_param', 'enemy.protector.ultimate_enabled'),
    'Ranged Ultimate': ('environment_param', 'enemy.ranged.ultimate_enabled'),
    "Tank's Ultimate": ('environment_param', 'enemy.tank.ultimate_enabled'),
}

_GOVERNED_NUMERIC_DESTINATIONS: Dict[str, Tuple[str, str]] = {
    'Standard Perks Bonus': ('mechanic_param', 'perk.standard_perks_bonus_pct'),
    'Improve Trade-off Perks': ('mechanic_param', 'perk.tradeoff_bonus_pct'),
    'Common Drop Chance': ('meta_progression_param', 'module.lab.common_drop_chance_bonus_pct'),
    'Rare Drop Chance': ('meta_progression_param', 'module.lab.rare_drop_chance_bonus_pct'),
    'Reroll Shards': ('meta_progression_param', 'module.lab.reroll_shards_bonus'),
    'Daily Mission Shards': ('meta_progression_param', 'module.lab.daily_mission_shards_bonus'),
    'Shatter Shards': ('meta_progression_param', 'module.lab.shatter_shards_bonus_pct'),
    'Module Coin Cost': ('meta_progression_param', 'module.lab.coin_cost_reduction_pct'),
    'Module Shards Cost': ('meta_progression_param', 'module.lab.shard_cost_reduction_pct'),
    'Starting Cash': ('meta_progression_param', 'economy.starting_cash_bonus'),
    'Max Interest': ('meta_progression_param', 'economy.max_interest_bonus'),
}
_GOVERNED_NUMERIC_DESTINATIONS.update(_ULTIMATE_DESTINATIONS)

_GOVERNED_NUMERIC_FORMULAS = {
    'Standard Perks Bonus': lambda level: float(level),
    'Improve Trade-off Perks': lambda level: float(level),
    'Reroll Shards': lambda level: float(level),
    'Common Drop Chance': lambda level: float(level) * 0.1,
    'Rare Drop Chance': lambda level: float(level) * 0.1,
    'Daily Mission Shards': lambda level: float(level),
    'Shatter Shards': lambda level: float(level) * 20.0,
}

_CARD_MASTERY_NAME_ALIASES = {
    'Package Chance Mastery': 'Recovery Package Chance Mastery',
}


def _coerce_level_bool(level: object) -> bool:
    try:
        return bool(level is not None and float(level) > 0)
    except (TypeError, ValueError):
        return bool(level)


def _coerce_level_number(level: object) -> float | None:
    try:
        return float(level)
    except (TypeError, ValueError):
        return None


def _parse_mastery_value_token(raw: str) -> Tuple[float | None, str]:
    token = str(raw or '').strip()
    if not token:
        return None, 'raw_text'
    cleaned = token.replace('+', '').replace(',', '').strip()
    if cleaned.startswith('x'):
        try:
            return float(cleaned[1:]), 'multiplier'
        except ValueError:
            return None, 'raw_text'
    if cleaned.endswith('%'):
        try:
            return float(cleaned[:-1]), 'resolved_value'
        except ValueError:
            return None, 'raw_text'
    if cleaned.endswith('s'):
        try:
            return float(cleaned[:-1]), 'resolved_value'
        except ValueError:
            return None, 'raw_text'
    try:
        return float(cleaned), 'resolved_value'
    except ValueError:
        return None, 'raw_text'


def _card_mastery_baseline(first_token: str) -> Tuple[float, str]:
    token = str(first_token or '').strip()
    if token.startswith('x'):
        return 1.0, 'multiplier'
    return 0.0, 'resolved_value'


@lru_cache(maxsize=1)
def _load_card_mastery_values() -> Dict[Tuple[str, int], Tuple[float, str]]:
    out: Dict[Tuple[str, int], Tuple[float, str]] = {}
    if not CARD_MASTERIES_PATH.exists():
        return out
    with CARD_MASTERIES_PATH.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            mastery_name = str(row.get('card_mastery') or '').strip()
            if not mastery_name:
                continue
            mastery_keys = [f'{mastery_name} Mastery']
            alias = _CARD_MASTERY_NAME_ALIASES.get(f'{mastery_name} Mastery')
            if alias is not None:
                mastery_keys.append(alias)
            baseline = _card_mastery_baseline(row.get('level_0', ''))
            for mastery_key in mastery_keys:
                out[(mastery_key, 0)] = baseline
            for level in range(10):
                value, value_type = _parse_mastery_value_token(row.get(f'level_{level}', ''))
                if value is not None:
                    for mastery_key in mastery_keys:
                        out[(mastery_key, level + 1)] = (value, value_type)
    return out


def _bind_account_metadata_row(row: StatInput, canonical_stats: Dict[str, Dict[str, str]], name: str, level: object) -> bool:
    destination = ACCOUNT_METADATA_DESTINATIONS.get(name)
    if destination is None:
        return False
    bind_destination(row, destination, canonical_stats, note=f'account_metadata_routed:{name}')
    if name in _BOOLEAN_ACCOUNT_METADATA_ROWS:
        _set_row_field(row, 'value', _coerce_level_bool(level))
        _set_row_field(row, 'value_type', 'bool')
    else:
        numeric = _coerce_level_number(level)
        if numeric is not None:
            _set_row_field(row, 'value', numeric)
            _set_row_field(row, 'value_type', 'resolved_value')
    return True


def _bind_capability_policy_row(row: StatInput, canonical_stats: Dict[str, Dict[str, str]], name: str, level: object) -> bool:
    destination = CAPABILITY_POLICY_DESTINATIONS.get(name)
    if destination is None:
        return False
    bind_destination(row, destination, canonical_stats, note=f'capability_policy_routed:{name}')
    if name in _BOOLEAN_CAPABILITY_POLICY_ROWS:
        _set_row_field(row, 'value', _coerce_level_bool(level))
        _set_row_field(row, 'value_type', 'bool')
    elif name in _TEXT_CAPABILITY_POLICY_ROWS:
        _set_row_field(row, 'value', '' if level is None else str(level))
        _set_row_field(row, 'value_type', 'raw_text')
    else:
        numeric = _coerce_level_number(level)
        if numeric is not None:
            _set_row_field(row, 'value', numeric)
            _set_row_field(row, 'value_type', 'resolved_value')
    return True


def _governed_numeric_destination(name: str) -> Tuple[str, str] | None:
    if name in _GOVERNED_NUMERIC_DESTINATIONS:
        return _GOVERNED_NUMERIC_DESTINATIONS[name]
    match = re.match(r'^Assist Module Bonus - (Armor|Cannon|Core|Generator)$', name)
    if match is not None:
        return _ASSIST_BONUS_DESTINATIONS[match.group(1)]
    match = re.match(r'^Assist Module Substats - (Armor|Cannon|Core|Generator)$', name)
    if match is not None:
        return _ASSIST_SUBSTAT_DESTINATIONS[match.group(1)]
    if name.endswith(' Mastery'):
        card_slug = slug_text(name[:-8]).replace(' ', '_')
        return 'runtime_mechanic_param', f'cards.{card_slug}.mastery_effect'
    return None


def _bind_governed_numeric_row(
    row: StatInput,
    canonical_stats: Dict[str, Dict[str, str]],
    name: str,
    level: object,
    lab_values: Dict[Tuple[str, int], float],
    lab_summary: Dict[str, Dict[str, float | str]],
    card_mastery_values: Dict[Tuple[str, int], Tuple[float, str]],
) -> bool:
    destination = _governed_numeric_destination(name)
    if destination is None:
        return False
    bind_destination(row, destination, canonical_stats, note=f'governed_numeric_routed:{name}')
    if name in _ULTIMATE_DESTINATIONS:
        _set_row_field(row, 'value', _coerce_level_bool(level))
        _set_row_field(row, 'value_type', 'bool')
        return True
    if name.endswith(' Mastery'):
        mastery_level = int(level) if isinstance(level, int) else 0 if level in {None, ''} else None
        mastery_key = (name, mastery_level) if mastery_level is not None else None
        mastery_value = card_mastery_values.get(mastery_key) if mastery_key is not None else None
        if mastery_value is not None:
            _set_row_field(row, 'value', mastery_value[0])
            _set_row_field(row, 'value_type', mastery_value[1])
            _set_row_field(row, 'notes', f'kb_card_mastery_resolved:{name}')
        elif level is not None:
            numeric = _coerce_level_number(level)
            if numeric is not None:
                _set_row_field(row, 'value', numeric)
                _set_row_field(row, 'value_type', 'level')
                _set_row_field(row, 'notes', f'governed_numeric_pending_value:{name}')
        return True
    formula = _GOVERNED_NUMERIC_FORMULAS.get(name)
    if formula is not None and level is not None:
        numeric = _coerce_level_number(level)
        if numeric is not None:
            _set_row_field(row, 'value', formula(numeric))
            _set_row_field(row, 'value_type', 'resolved_value')
            return True
    exact_values: Dict[int, float] | None = None
    if name == 'Module Coin Cost':
        exact_values = _load_module_coin_cost_values()
    elif name == 'Module Shards Cost':
        exact_values = _load_module_shard_cost_values()
    elif name == 'Starting Cash':
        exact_values = _load_starting_cash_values()
    else:
        match = re.match(r'^Assist Module Bonus - (Armor|Cannon|Core|Generator)$', name)
        if match is not None:
            exact_values = _load_assist_module_bonus_values()
        match = re.match(r'^Assist Module Substats - (Armor|Cannon|Core|Generator)$', name)
        if match is not None:
            exact_values = _load_assist_module_substat_values()
    if exact_values is not None and isinstance(level, int) and level in exact_values:
        _set_row_field(row, 'value', exact_values[level])
        _set_row_field(row, 'value_type', 'resolved_value')
        return True
    if exact_values is not None and level == 0:
        _set_row_field(row, 'value', 0.0)
        _set_row_field(row, 'value_type', 'resolved_value')
        return True
    lab_value = _lab_value_with_fallback(name, level if isinstance(level, int) else None, lab_values, lab_summary)
    if lab_value is not None:
        _set_row_field(row, 'value', lab_value)
        _set_row_field(row, 'value_type', 'resolved_value')
    elif level is not None:
        numeric = _coerce_level_number(level)
        if numeric is not None:
            _set_row_field(row, 'value', numeric)
            _set_row_field(row, 'value_type', 'level')
            _set_row_field(row, 'notes', f'governed_numeric_pending_value:{name}')
    return True


@lru_cache(maxsize=1)
def _load_perk_entities() -> Dict[str, Dict[str, object]]:
    out: Dict[str, Dict[str, object]] = {}
    if not PERK_ENTITY_REGISTRY_PATH.exists():
        return out
    with PERK_ENTITY_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            perk_id = row.get('perk_id', '').strip()
            if not perk_id:
                continue
            try:
                max_picks = int(row.get('max_picks', '1'))
            except (TypeError, ValueError):
                max_picks = 1
            out[perk_id] = {
                'perk_name': row.get('perk_name', '').strip(),
                'category': row.get('category', '').strip(),
                'max_picks': max_picks,
                'stacking_type': row.get('stacking_type', '').strip(),
                'effect_count': row.get('effect_count', '').strip(),
                'status': row.get('status', '').strip(),
            }
    return out


@lru_cache(maxsize=1)
def _load_perk_effects() -> Dict[str, List[Dict[str, str]]]:
    out: Dict[str, List[Dict[str, str]]] = {}
    if not PERK_EFFECT_REGISTRY_PATH.exists():
        return out
    with PERK_EFFECT_REGISTRY_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            perk_id = row.get('perk_id', '').strip()
            if not perk_id:
                continue
            out.setdefault(perk_id, []).append(row)
    return out


def load_perk_entities() -> Dict[str, Dict[str, object]]:
    """Public evaluator/app-facing surface for perk entity metadata."""
    return _load_perk_entities()


def load_perk_effects() -> Dict[str, List[Dict[str, str]]]:
    """Public evaluator/app-facing surface for perk effect metadata."""
    return _load_perk_effects()


def load_card_mastery_values() -> Dict[Tuple[str, int], Tuple[float, str]]:
    """Public app-facing surface for card mastery ladder values."""
    return _load_card_mastery_values()


def scaled_perk_value(
    *,
    perk_meta: Dict[str, object],
    perk_effect_meta: Dict[str, object],
    perk_id: str,
    operation: str,
    raw_value: str,
    picks: int,
    effect_index: str,
    perk_lab_state: Dict[str, float],
) -> float | None:
    """Public app-facing wrapper for perk effect value scaling."""
    return _scaled_perk_value(
        perk_meta=perk_meta,
        perk_effect_meta=perk_effect_meta,
        perk_id=perk_id,
        operation=operation,
        raw_value=raw_value,
        picks=picks,
        effect_index=effect_index,
        perk_lab_state=perk_lab_state,
    )


@lru_cache(maxsize=1)
def _load_module_substat_units() -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not MODULE_SUBSTATS_TABLE_PATH.exists():
        return out
    with MODULE_SUBSTATS_TABLE_PATH.open(newline='') as f:
        for row in csv.DictReader(f):
            name = row.get('substat', '').strip()
            unit = row.get('unit', '').strip().lower()
            if name and unit and name not in out:
                out[name] = unit
    return out


def _make_instance_contributor_id(base_id: str | None, *, source_name: str, role: str | None = None, sub_name: str | None = None) -> str | None:
    if not base_id:
        return base_id
    parts = [base_id, slug_text(source_name)]
    if role:
        parts.append(slug_text(role))
    if sub_name:
        parts.append(slug_text(sub_name))
    return '@@'.join(parts)


def _append(out: List[StatInput], row: StatInput) -> None:
    out.append(row)



def compile_stat_inputs(
    account_state: AccountState,
    *,
    preset_name: str | None = None,
    state_mode: str = 'start_of_run',
    card_preset_name: str | None = None,
    module_preset_name: str | None = None,
    perk_preset_name: str | None = None,
    perks_enabled: bool | None = None,
    scenario_projection_state: ScenarioProjectionState | None = None,
) -> List[StatInput]:
    preset = preset_name or account_state.default_preset
    active_perk_preset = getattr(account_state, 'active_perk_preset', None)
    perk_preset_namespace_class = getattr(account_state, 'perk_preset_namespace_class', 'canonical')
    bound = bind_preset_family(
        preset_name=preset,
        state_mode=state_mode,
        perk_namespace_class=perk_preset_namespace_class,
        explicit_card_preset_name=card_preset_name,
        explicit_module_preset_name=module_preset_name,
        explicit_perk_preset_name=perk_preset_name,
        active_perk_preset_name=active_perk_preset,
        perks_enabled=perks_enabled,
    )
    preset = bound.preset_name
    card_preset = bound.card_preset_name
    module_preset = bound.module_preset_name
    perk_preset = bound.perk_preset_name
    canonical_output_perk_preset = sanitize_preset_name_for_canonical_output(
        perk_preset,
        namespace_class=perk_preset_namespace_class,
        fallback_preset_name=preset,
    )
    perks_enabled = bound.perks_enabled
    state_mode = normalize_state_mode(state_mode)
    resolved_projection_state = scenario_projection_state or projection_state_for_mode(state_mode)
    mapping_index, canonical_stats, alias_index, relic_index, family_slug_index = compiler_routing_indexes()
    lab_values = _load_lab_values()
    lab_summary = _load_lab_summary_lookup()
    workshop_values = _load_workshop_value_lookup()
    card_ladders = _load_card_ladders()
    card_effect_targets = load_card_effect_targets()
    module_substat_units = _load_module_substat_units()
    perk_entities = _load_perk_entities()
    perk_effects = _load_perk_effects()
    module_substat_values = load_module_substat_values()
    module_unique_effect_values = load_module_unique_effect_values()
    assist_efficiency_lookup = load_assist_efficiency_lookup()
    card_mastery_values = _load_card_mastery_values()
    lab_application_registry = load_lab_application_registry()
    uw_lab_wiki_values = _load_uw_lab_wiki_values()
    bot_track_values = _load_bot_track_values()
    bot_lab_rules = _load_bot_lab_rules()
    guardian_track_values = _load_guardian_track_values()
    uw_track_values = _load_uw_track_values()
    uw_plus_values = _load_uw_plus_values()
    guardian_scout_values = _load_guardian_scout_values()
    out: List[StatInput] = []

    # Labs: exact KB ladders where available; otherwise use the bundled lab application registry.
    for name, level in account_state.labs.items():
        row = StatInput(stat_name=name, source_family='lab', source_name=name, value=level, value_type='level', stage='account_state', provenance='IDS::Labs')
        contributor_id = LAB_IDS_TO_CONTRIBUTOR.get(name)
        if contributor_id is not None:
            bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
            lab_value = _lab_value_with_fallback(name, level, lab_values, lab_summary)
            if name == 'Wall Invincibility' and level == 0:
                lab_value = 0.0
            if name == 'Wall Thorns' and level is not None and lab_value is None:
                lab_value = level / 100.0
            if lab_value is not None:
                _set_row_field(row, 'value', lab_value)
                _set_row_field(row, 'value_type', 'resolved_value')
        else:
            app = lab_application_registry.get(name) or lab_application_registry.get(slug_text(name))
            if app is not None:
                destination = LAB_APPLICATION_TARGET_TO_DESTINATION.get((app['target_entity'], app['target_attribute']))
                if destination is not None:
                    bind_destination(row, destination, canonical_stats, note='kb_lab_application_registry_routed')
                    operation_type = str(app.get('operation_type', '')).strip().lower()
                    if operation_type in {'enable', 'set_bool', 'set_boolean'}:
                        _set_row_field(row, 'value', bool(level and float(level) > 0))
                        _set_row_field(row, 'value_type', 'bool')
                    else:
                        lab_value = _lab_value_with_fallback(name, level, lab_values, lab_summary)
                        if lab_value is not None:
                            _set_row_field(row, 'value', lab_value)
                            _set_row_field(row, 'value_type', 'resolved_value')
                    if name == 'Missiles Explosion' and bool(level and float(level) > 0):
                        split_row = StatInput(**{field: getattr(row, field) for field in StatInput.__dataclass_fields__.keys()})
                        _set_row_field(split_row, 'stat_name', 'Missiles Explosion::Base Radius')
                        _set_row_field(split_row, 'source_family', 'lab')
                        _set_row_field(split_row, 'source_name', 'Missiles Explosion')
                        _set_row_field(split_row, 'value', 0.30)
                        _set_row_field(split_row, 'value_type', 'resolved_value')
                        bind_destination(split_row, ('mechanic_param', 'uw.smart_missiles.explosion_radius_m'), canonical_stats, note='kb_lab_unlock_base_radius_split:missiles_explosion')
                        _append(out, split_row)
                    if name == 'Missile Barrage' and bool(level and float(level) > 0):
                        split_row = StatInput(**{field: getattr(row, field) for field in StatInput.__dataclass_fields__.keys()})
                        _set_row_field(split_row, 'stat_name', 'Missile Barrage::Base Quantity')
                        _set_row_field(split_row, 'source_family', 'lab')
                        _set_row_field(split_row, 'source_name', 'Missile Barrage')
                        _set_row_field(split_row, 'value', 20.0)
                        _set_row_field(split_row, 'value_type', 'resolved_value')
                        bind_destination(split_row, ('mechanic_param', 'uw.smart_missiles.barrage_quantity'), canonical_stats, note='kb_lab_unlock_base_quantity_split:missile_barrage')
                        _append(out, split_row)
                    if name == 'Poison Swamp Stun' and bool(level and float(level) > 0):
                        split_row = StatInput(**{field: getattr(row, field) for field in StatInput.__dataclass_fields__.keys()})
                        _set_row_field(split_row, 'stat_name', 'Poison Swamp Stun::Base Chance')
                        _set_row_field(split_row, 'source_family', 'lab')
                        _set_row_field(split_row, 'source_name', 'Poison Swamp Stun')
                        _set_row_field(split_row, 'value', 5.0)
                        _set_row_field(split_row, 'value_type', 'resolved_value')
                        bind_destination(split_row, ('mechanic_param', 'uw.poison_swamp.stun_chance_pct'), canonical_stats, note='kb_lab_unlock_base_chance_split:poison_swamp_stun')
                        _append(out, split_row)
                        split_row = StatInput(**{field: getattr(row, field) for field in StatInput.__dataclass_fields__.keys()})
                        _set_row_field(split_row, 'stat_name', 'Poison Swamp Stun::Base Duration')
                        _set_row_field(split_row, 'source_family', 'lab')
                        _set_row_field(split_row, 'source_name', 'Poison Swamp Stun')
                        _set_row_field(split_row, 'value', 1.0)
                        _set_row_field(split_row, 'value_type', 'resolved_value')
                        bind_destination(split_row, ('mechanic_param', 'uw.poison_swamp.stun_duration_seconds'), canonical_stats, note='kb_lab_unlock_base_duration_split:poison_swamp_stun')
                        _append(out, split_row)
                else:
                    _set_row_field(row, 'notes', 'kb_lab_application_registry_unhandled_target')
            else:
                if name == 'Wall Rebuild':
                    bind_destination(row, ('canonical_stat', 'wall_rebuild_seconds'), canonical_stats, note='kb_manual_wall_rebuild_lab_routed')
                    lab_value = _lab_value_with_fallback(name, level, lab_values, lab_summary)
                    if lab_value is not None:
                        _set_row_field(row, 'value', lab_value)
                        _set_row_field(row, 'value_type', 'resolved_value')
                elif name == 'Extra Extra Orbs':
                    bind_destination(row, ('canonical_stat', 'tower_orb_count'), canonical_stats, note='kb_manual_extra_extra_orbs_lab_routed')
                    if level is not None:
                        _set_row_field(row, 'value', float(level))
                        _set_row_field(row, 'value_type', 'resolved_value')
                elif name == 'Defense Absolute':
                    bind_destination(row, ('canonical_stat', 'tower_defense_absolute'), canonical_stats, note='kb_manual_defense_absolute_lab_routed')
                    lab_value = _lab_value_with_fallback(name, level, lab_values, lab_summary)
                    if lab_value is not None:
                        _set_row_field(row, 'value', lab_value)
                        _set_row_field(row, 'value_type', 'resolved_value')
                elif name == 'Damage / Meter':
                    bind_destination(row, ('canonical_stat', 'tower_damage_per_meter_multiplier'), canonical_stats, note='kb_manual_damage_per_meter_lab_routed')
                    lab_value = _lab_value_with_fallback(name, level, lab_values, lab_summary)
                    if lab_value is not None:
                        _set_row_field(row, 'value', lab_value)
                        _set_row_field(row, 'value_type', 'resolved_value')
                elif name == 'Death Wave Health':
                    dw_state = account_state.ultimate_weapons.get('Death Wave')
                    if not resolved_projection_state.death_wave_health:
                        continue
                    if str(getattr(dw_state, 'unlocked', '')).strip().lower() == 'true' and level is not None:
                        bind_destination(row, ('canonical_stat', 'tower_hp'), canonical_stats, note='kb_manual_death_wave_health_lab_routed')
                        _set_row_field(row, 'value', 5.0 + 0.25 * float(level))
                        _set_row_field(row, 'value_type', 'multiplier')
                        _set_row_field(row, 'notes', 'kb_manual_death_wave_health_lab_routed:ep_formula_eph_health_dwhp_multiplier')
                    else:
                        _set_row_field(row, 'notes', 'death_wave_health_present_but_uw_not_owned_or_level_missing')
                else:
                    dest = _UW_LAB_DIRECT_DESTINATION.get(name)
                    if dest is not None:
                        bind_destination(row, dest, canonical_stats, note=f'kb_uw_lab_direct_routed:{name}')
                        if dest[0] == 'capability':
                            _set_row_field(row, 'value', bool(level and float(level) > 0))
                            _set_row_field(row, 'value_type', 'bool')
                            _set_row_field(row, 'notes', f'kb_lab_capability_{"resolved" if row.value else "locked"}:{name}')
                        elif name == 'Max Rend Armor Multiplier' and level is not None:
                            _set_row_field(row, 'value', 0.25 * float(level))
                            _set_row_field(row, 'value_type', 'resolved_value')
                            _set_row_field(row, 'notes', 'kb_lab_formula_verified:Max Rend Armor Multiplier:+0.25_per_level')
                        elif name in BOT_LAB_BINDINGS and level is not None:
                            rule_key, fallback_step = BOT_LAB_BINDINGS[name]
                            rule = bot_lab_rules.get(rule_key, {})
                            per_level = rule.get('effect_per_level_seconds')
                            if per_level is None:
                                per_level = fallback_step
                            _set_row_field(row, 'value', float(level) * float(per_level))
                            _set_row_field(row, 'value_type', 'resolved_value')
                            _set_row_field(row, 'notes', f'kb_bot_lab_formula_verified:{name}')
                        else:
                            wiki_val = uw_lab_wiki_values.get((name, level)) if level is not None else None
                            if wiki_val is not None:
                                _set_row_field(row, 'value', wiki_val)
                                _set_row_field(row, 'value_type', 'resolved_value')
                                _set_row_field(row, 'notes', f'kb_uw_lab_wiki_verified:{name}')
                            elif level is not None and level > 0:
                                _set_row_field(row, 'value', float(level))
                                _set_row_field(row, 'value_type', 'level')
                                _set_row_field(row, 'notes', f'kb_lab_routed_level_pending_value:{name}')
                    elif name in PARSER_DROP_ROWS:
                        continue
                    elif name in ACCOUNT_METADATA_ROWS:
                        if not _bind_account_metadata_row(row, canonical_stats, name, level):
                            _set_row_field(row, 'notes', f'account_metadata_pending_mapping:{name}')
                    elif name in CAPABILITY_POLICY_ROWS:
                        if not _bind_capability_policy_row(row, canonical_stats, name, level):
                            _set_row_field(row, 'notes', f'capability_policy_pending_mapping:{name}')
                    elif name in GOVERNED_NUMERIC_ROWS:
                        if not _bind_governed_numeric_row(
                            row,
                            canonical_stats,
                            name,
                            level,
                            lab_values,
                            lab_summary,
                            card_mastery_values,
                        ):
                            _set_row_field(row, 'notes', f'governed_numeric_pending_mapping:{name}')
                    else:
                        _set_row_field(row, 'notes', 'kb_routing_pending_for_lab_label')
        _append(out, row)

    # Workshop: exact contributor routing + value lookup where the KB contains ladders.
    for name, entry in account_state.workshop.items():
        level = entry.max_level if resolved_projection_state.max_workshop and entry.max_level is not None else entry.preset_levels.get(preset)
        row = StatInput(stat_name=name, source_family='workshop', source_name=name, value=level, value_type='level', stage='loadout_resolved', preset_name=preset, provenance='IDS::WS')
        if resolved_projection_state.max_workshop and entry.max_level is not None:
            _set_row_field(row, 'notes', 'projection_state=max_workshop:using_workshop_max_level')
        contributor_id = WORKSHOP_IDS_TO_CONTRIBUTOR.get(name)
        if contributor_id is not None:
            bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
            if level is not None and (name, level) in workshop_values:
                _set_row_field(row, 'value', workshop_values[(name, level)])
                _set_row_field(row, 'value_type', 'resolved_value')
            elif level is not None and name in WORKSHOP_FORMULA_VALUES:
                _set_row_field(row, 'value', WORKSHOP_FORMULA_VALUES[name](level))
                _set_row_field(row, 'value_type', 'resolved_value')
                _set_row_field(row, 'notes', (row.notes or '') + ':kb_workshop_summary_formula_derived')
            else:
                _set_row_field(row, 'notes', ((row.notes or '') + ':unresolved_workshop_level_no_value_formula').strip(':'))
        else:
            _set_row_field(row, 'notes', 'kb_routing_pending_for_workshop_label')
        _append(out, row)

    # Enhancements: use typed WS+ tracks so selected preset lane determines level/value.
    enhancement_tracks = getattr(account_state, 'workshop_enhancement_tracks', {}) or {}
    if enhancement_tracks:
        typed_enhancement_rows = []
        for track in enhancement_tracks.values():
            # For max_workshop projections, keep WS+ at the selected preset lane.
            # Workshop-max semantics should not implicitly promote enhancement tracks.
            level = track.preset_levels.get(preset)
            value = (1.0 + float(level) / 100.0) if level is not None else track.current_multiplier
            typed_enhancement_rows.append((track.name, level, value, track.max_level))
    else:
        typed_enhancement_rows = []
        for cells in account_state.workshop_enhancements.rows:
            if not cells or not cells[0].strip():
                continue
            name = cells[0].strip()
            value = None
            for idx in [1, 2, 3]:
                if idx < len(cells):
                    try:
                        value = float(cells[idx])
                        break
                    except (ValueError, TypeError):
                        continue
            typed_enhancement_rows.append((name, None, value, None))
    for name, level, value, max_level in typed_enhancement_rows:
        alias_name = name.rstrip('+').strip()
        if value is None:
            continue
        row = StatInput(stat_name=name, source_family='enhancement', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::WS+')
        _set_row_field(row, 'raw_level', level)
        _set_row_field(row, 'resolved_value', float(value))
        _set_row_field(row, 'resolved_unit', 'x')
        if resolved_projection_state.max_workshop and max_level is not None:
            _set_row_field(row, 'notes', 'projection_state=max_workshop:using_ws_plus_max_level')
        bind_alias_destination(row, alias_name, alias_index, canonical_stats, note='kb_alias_routed_enhancement')
        alias_slug = slug_text(alias_name)
        if alias_slug == 'enemy level skips':
            for extra_id in ('enhancements__tower__enemy_attack_level_skip__multiplier', 'enhancements__tower__enemy_health_level_skip__multiplier'):
                extra = StatInput(stat_name=name, source_family='enhancement', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::WS+', notes='kb_dual_routed_enhancement')
                bind_kb_fields(extra, extra_id, mapping_index, canonical_stats)
                _append(out, extra)
        if alias_slug == 'coin bonus':
            extra = StatInput(stat_name=name, source_family='enhancement', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::WS+', notes='kb_dual_routed_enhancement:coins_per_kill_spillover')
            bind_destination(extra, ('canonical_stat', 'coins_per_kill_bonus'), canonical_stats, note='kb_dual_routed_enhancement:coins_per_kill_spillover')
            if row.value_type == 'resolved_value' and isinstance(row.value, (int, float)) and 0.0 <= float(row.value) <= 1.0:
                dest = row.destination_id or ''
                if dest.endswith('_pct') or dest.endswith('.chance_pct') or dest.endswith('.slow_pct') or dest.endswith('.damage_reduction_pct'):
                    _set_row_field(row, 'value', float(row.value) * 100.0)
                    _set_row_field(row, 'notes', f"{row.notes or 'ids_uw_current_value_preserved'}; normalized_fraction_to_pct_points")
            _append(out, row)
            _append(out, extra)
            continue
        if alias_slug == 'free upgrades':
            _append(out, row)
            continue
        if alias_slug == 'rend armor mult':
            extra = StatInput(stat_name=name, source_family='enhancement', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::WS+', notes='kb_dual_routed_enhancement:max_rend_surface')
            bind_destination(extra, ('canonical_stat', 'max_rend_mult'), canonical_stats, note='kb_dual_routed_enhancement:max_rend_surface')
            _append(out, extra)
        else:
            _append(out, row)

    # Theme/song passive bonus: fold the bundled cosmetic coin multiplier into the calculator coin surface.
    if getattr(account_state, 'theme_song_coin_multiplier', None) is not None:
        row = StatInput(stat_name='Theme Song Coin Bonus', source_family='theme_song', source_name='Themes & Songs', value=account_state.theme_song_coin_multiplier, value_type='resolved_value', stage='account_state', provenance='IDS::Themes & Songs', notes='kb_theme_song_preserved_on_cosmetic_helper_surface', contributor_id='theme_song__global__coin_bonus__multiplier')
        bind_kb_fields(row, 'theme_song__global__coin_bonus__multiplier', mapping_index, canonical_stats)
        _append(out, row)

    # Player-meta helper surfaces used by KB-aligned all-coin composition.
    player_meta = getattr(account_state, 'player_meta', {}) or {}
    helper_meta_specs = [
        ('Disable Ads', 'player_stuff__flag__disable_ads__boolean', 'bool'),
        ('Starter Pack', 'player_stuff__flag__starter_pack__boolean', 'bool'),
        ('Epic Pack', 'player_stuff__flag__epic_pack__boolean', 'bool'),
        ('Farming Tier', 'player_stuff__profile__farming_tier__enum', 'raw_text'),
        ('Coin Multiplier', 'player_stuff__derived__coin_multiplier__enum', 'raw_text'),
    ]
    for meta_name, contributor_id, value_type in helper_meta_specs:
        raw_value = player_meta.get(meta_name)
        if raw_value is None:
            continue
        value = raw_value
        if value_type == 'bool':
            value = str(raw_value).strip().lower() in {'true', '1', 'yes', 'unlocked'}
        row = StatInput(stat_name=meta_name, source_family='player_stuff', source_name=meta_name, value=value, value_type=value_type, stage='account_state', provenance='IDS::Player & Stuff')
        bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
        _append(out, row)

    # Relics: registry-only direct values from IDS. These are already account-state effects, not spend levels.
    for name, value in account_state.relics.items():
        if value is None:
            continue
        if slug_text(name) == 'bot range':
            for dest in BOT_RANGE_CANONICALS:
                row = StatInput(stat_name=name, source_family='relic', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::Relics')
                bind_destination(row, dest, canonical_stats, note='kb_bot_range_relic_promoted')
                _append(out, row)
            continue
        row = StatInput(stat_name=name, source_family='relic', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::Relics')
        if name in ACCOUNT_METADATA_ROWS and _bind_account_metadata_row(row, canonical_stats, name, value):
            _append(out, row)
            continue
        contributor_id = relic_index.get(slug_text(name)) or RELIC_CONTRIBUTOR_OVERRIDES.get(slug_text(name))
        if contributor_id:
            bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
        else:
            override_dest = RELIC_ALIAS_OVERRIDES.get(slug_text(name))
            if override_dest is not None:
                bind_destination(row, override_dest, canonical_stats, note='kb_relic_override_routed')
            else:
                bind_alias_destination(row, name, alias_index, canonical_stats, note='kb_alias_routed_relic')
        _append(out, row)

    # Vault: preserve exact scalar values and unlock booleans.
    for name, value in account_state.vault.items():
        if slug_text(name) == 'bot range':
            for dest in BOT_RANGE_CANONICALS:
                row = StatInput(stat_name=name, source_family='vault', source_name=name, value=value, value_type='resolved_value', stage='account_state', provenance='IDS::Vault')
                bind_destination(row, dest, canonical_stats, note='kb_bot_range_vault_promoted')
                _append(out, row)
            continue
        value_type = 'bool' if isinstance(value, bool) else ('resolved_value' if isinstance(value, (int, float)) else 'raw_text')
        row = StatInput(stat_name=name, source_family='vault', source_name=name, value=value, value_type=value_type, stage='account_state', provenance='IDS::Vault')
        if name in ACCOUNT_METADATA_ROWS and _bind_account_metadata_row(row, canonical_stats, name, value):
            _append(out, row)
            continue
        contributor_id = mapping_lookup_for_family_name(family_slug_index, 'vault', name)
        if contributor_id:
            bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
        else:
            numeric_override = VAULT_NUMERIC_OVERRIDES.get(slug_text(name)) if not isinstance(value, bool) else None
            fallback_dest = VAULT_BOOLEAN_FLAGS.get(slug_text(name)) if isinstance(value, bool) else None
            if numeric_override is not None:
                bind_destination(row, numeric_override, canonical_stats, note='kb_vault_numeric_override_routed')
            elif fallback_dest is not None:
                bind_destination(row, fallback_dest, canonical_stats, note='kb_vault_boolean_flag_routed')
            else:
                bind_alias_destination(row, name, alias_index, canonical_stats, note='kb_alias_routed_vault')
        _append(out, row)

    bot_slug_map = {
        'gold bot': 'golden',
        'golden bot': 'golden',
        'amp bot': 'amplify',
        'amplify bot': 'amplify',
        'flame bot': 'flame',
        'thunder bot': 'thunder',
    }
    owned_bot_aliases = set()
    for name in account_state.bots:
        key = slug_text(str(name)).replace('_', ' ')
        owned_bot_aliases.add(key)
        owned_bot_aliases.add(key.replace('golden', 'gold'))
        owned_bot_aliases.add(key.replace('amplify', 'amp'))
    for source_name, bot_slug in bot_slug_map.items():
        unlock_row = StatInput(
            stat_name=f'{source_name.title()}::Unlocked',
            source_family='bot_unlock',
            source_name=source_name.title(),
            value=(source_name in owned_bot_aliases),
            value_type='bool',
            stage='account_state',
            provenance='IDS::Bots',
            notes='ids_bot_unlock_flag_preserved',
        )
        _set_row_field(unlock_row, 'destination_object_type', 'capability')
        _set_row_field(unlock_row, 'destination_id', f'bot.{bot_slug}.owned')
        _set_row_field(unlock_row, 'resolver_id', 'standard_bool')
        _set_row_field(unlock_row, 'kb_mapped', True)
        _append(out, unlock_row)

    # Bots: route medal-funded tracks into mechanic_param canonicals via KB contributor mappings.
    typed_bot_tracks = getattr(account_state, 'bot_upgrade_tracks', {}) or {}
    if typed_bot_tracks:
        bot_track_rows = [
            (bot_name, track.track_name, track.level, track.resolved_value, track.resolved_unit)
            for bot_name, tracks in typed_bot_tracks.items()
            for track in tracks
        ]
    else:
        bot_track_rows = [
            (bot_name, attr, level, None, None)
            for bot_name, upgrades in account_state.bot_upgrades.items()
            for attr, level in upgrades.items()
        ]
    for bot_name, attr, level, ids_resolved_value, ids_resolved_unit in bot_track_rows:
        if level is None:
            continue
        binding = BOT_UPGRADE_BINDINGS.get((bot_name, attr))
        contributor_id, track_name = binding if binding is not None else (None, None)
        resolved = bot_track_values.get((bot_name, track_name, level)) if track_name is not None and level is not None else None
        row = StatInput(stat_name=f'{bot_name}::{attr}', source_family='bot', source_name=bot_name, value=resolved if resolved is not None else level, value_type='resolved_value' if resolved is not None else 'level', stage='account_state', provenance='IDS::Bots', notes='kb_bot_track_resolved' if resolved is not None else 'runtime_surface_preserved_pending_bot_track_lookup')
        _set_row_field(row, 'raw_level', level)
        _set_row_field(row, 'resolved_value', float(resolved if resolved is not None else ids_resolved_value) if (resolved is not None or ids_resolved_value is not None) else None)
        _set_row_field(row, 'resolved_unit', ids_resolved_unit)
        if contributor_id is not None:
            bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
            _set_row_field(row, 'kb_mapped', resolved is not None)
        else:
            _set_row_field(row, 'destination_object_type', 'runtime_mechanic_param')
            bot_slug = slug_text(bot_name).replace(' ', '_')
            attr_slug = (track_name or slug_text(attr)).replace(' ', '_')
            _set_row_field(row, 'destination_id', f'bot.{bot_slug}.{attr_slug}')
            _set_row_field(row, 'resolver_id', 'standard_scalar_param')
            _set_row_field(row, 'kb_mapped', resolved is not None)
        _append(out, row)

    guardian_attr_map = {
        'cooldown': 'cooldown',
        'duration': 'duration',
        'range bonus': 'range_bonus',
        'cash bonus': 'cash_bonus',
        'recovery amount': 'recovery_amount',
        'max recovery': 'max_recovery',
        'percentage': 'percentage',
        'multiplier': 'multiplier',
        'targets': 'targets',
        'find chance': 'find_chance',
        'double find chance': 'double_find_chance',
    }
    typed_guardian_tracks = getattr(account_state, 'guardian_tracks', {}) or {}
    if typed_guardian_tracks:
        guardian_rows = [
            (guardian_name, track.track_name, track.level, track.resolved_value, track.resolved_unit)
            for guardian_name, tracks in typed_guardian_tracks.items()
            for track in tracks
        ]
    else:
        current_guardian = None
        guardian_rows = []
        for row_cells in account_state.guardians.rows:
            name = row_cells[0].strip() if len(row_cells) > 0 else ''
            attr = row_cells[2].strip() if len(row_cells) > 2 else ''
            display = row_cells[4].strip() if len(row_cells) > 4 else ''
            if name and name not in {'true', 'false'}:
                current_guardian = name
            if current_guardian and attr and display:
                level_token = display.split('|', 1)[0].strip()
                try:
                    level = int(float(level_token))
                except ValueError:
                    level = None
                guardian_rows.append((current_guardian, attr, level, None, None))
    for current_guardian, attr, level, ids_resolved_value, ids_resolved_unit in guardian_rows:
        g_attr = guardian_attr_map.get(slug_text(attr), slug_text(attr).replace(' ', '_'))
        resolved = guardian_track_values.get((current_guardian, g_attr, level)) if level is not None else None
        if resolved is None and current_guardian == 'Scout' and level is not None:
            resolved = guardian_scout_values.get((attr, level))
        row = StatInput(stat_name=f'{current_guardian}::{attr}', source_family='guardian', source_name=current_guardian, value=resolved if resolved is not None else level, value_type='resolved_value' if resolved is not None else 'level', stage='account_state', provenance='IDS::Guardians', notes='kb_guardian_track_resolved' if resolved is not None else 'runtime_surface_preserved_pending_guardian_track_lookup')
        _set_row_field(row, 'raw_level', level)
        _set_row_field(row, 'resolved_value', float(resolved if resolved is not None else ids_resolved_value) if (resolved is not None or ids_resolved_value is not None) else None)
        _set_row_field(row, 'resolved_unit', ids_resolved_unit)
        destination = GUARDIAN_DESTINATION_OVERRIDES.get((current_guardian, attr))
        if destination is not None:
            bind_destination(row, destination, canonical_stats, note='kb_guardian_override_routed')
        else:
            _set_row_field(row, 'destination_object_type', 'runtime_mechanic_param')
            guardian_slug = slug_text(current_guardian).replace(' ', '_')
            _set_row_field(row, 'destination_id', f'guardian.{guardian_slug}.{g_attr}')
            _set_row_field(row, 'resolver_id', 'standard_scalar_param')
            _set_row_field(row, 'kb_mapped', resolved is not None)
        _append(out, row)

    # UWs and UW+: resolve exact track values from bundled ladders and registry-driven track order.
    for uw_name, uw in account_state.ultimate_weapons.items():
        uw_slug = slug_text(uw_name).replace(' ', '_')
        unlocked_bool = str(getattr(uw, 'unlocked', '')).strip().lower() == 'true'
        unlock_row = StatInput(
            stat_name=f'{uw_name}::Unlocked',
            source_family='uw_unlock',
            source_name=uw_name,
            value=unlocked_bool,
            value_type='bool',
            stage='account_state',
            provenance='IDS::UWs',
            notes='ids_uw_unlock_flag_preserved',
        )
        _set_row_field(unlock_row, 'destination_object_type', 'capability')
        _set_row_field(unlock_row, 'destination_id', f'uw.{uw_slug}.owned')
        _set_row_field(unlock_row, 'resolver_id', 'standard_bool')
        _set_row_field(unlock_row, 'kb_mapped', True)
        _append(out, unlock_row)

        typed_tracks = getattr(account_state, 'uw_tracks', {}).get(uw_name, [])
        if typed_tracks:
            uw_track_rows = [(track.track_name, track.level, track.resolved_value) for track in typed_tracks]
        else:
            uw_track_rows = []
            for idx, raw_level in enumerate(uw.track_levels):
                try:
                    level = int(str(raw_level).strip())
                except ValueError:
                    level = None
                track_name = f'track_{idx+1}'
                ids_actual_value = uw.track_values[idx] if idx < len(uw.track_values) else None
                uw_track_rows.append((track_name, level, ids_actual_value))
        for track_name, level, ids_actual_value in uw_track_rows:
            resolved = ids_actual_value if ids_actual_value is not None else (uw_track_values.get((uw_name, track_name, level)) if level is not None else None)
            if resolved is None and level is not None and uw_name == 'Golden Tower' and track_name == 'Duration':
                resolved = 15.0 + float(level)
            note = 'ids_uw_current_value_preserved' if ids_actual_value is not None else ('kb_uw_track_resolved' if resolved is not None else 'runtime_surface_preserved_pending_uw_track_lookup')
            row = StatInput(stat_name=f'{uw_name}::{track_name}', source_family='uw', source_name=uw_name, value=resolved if resolved is not None else level, value_type='resolved_value' if resolved is not None else 'level', stage='account_state', provenance='IDS::UWs', notes=note)
            _set_row_field(row, 'raw_level', level)
            _set_row_field(row, 'resolved_value', float(resolved) if resolved is not None else None)
            contributor_id = UW_CONTRIBUTOR_OVERRIDES.get((uw_name, track_name)) or uw_contributor_id(uw_name, track_name)
            if contributor_id in mapping_index:
                bind_kb_fields(row, contributor_id, mapping_index, canonical_stats)
            else:
                destination = UW_MECHANIC_DESTINATION_OVERRIDES.get((uw_name, track_name))
                if destination is not None:
                    bind_destination(row, destination, canonical_stats, note='kb_uw_override_routed')
                else:
                    _set_row_field(row, 'destination_object_type', 'mechanic_param')
                    track_slug = slug_text(track_name).replace(' ', '_')
                    _set_row_field(row, 'destination_id', f'uw.{uw_slug}.{track_slug}')
                    _set_row_field(row, 'resolver_id', 'standard_scalar_param')
                    _set_row_field(row, 'kb_mapped', resolved is not None)
            if row.value_type == 'resolved_value' and isinstance(row.value, (int, float)) and 0.0 <= float(row.value) <= 1.0:
                dest = row.destination_id or ''
                if dest.endswith('_pct') or dest.endswith('.chance_pct') or dest.endswith('.slow_pct') or dest.endswith('.damage_reduction_pct'):
                    _set_row_field(row, 'value', float(row.value) * 100.0)
                    _set_row_field(row, 'notes', f"{row.notes or 'ids_uw_current_value_preserved'}; normalized_fraction_to_pct_points")
            _append(out, row)
    for track_name, track in account_state.uw_plus_tracks.items():
        level = None
        token = track.display_token.split('|',1)[0].strip() if track.display_token else ''
        if token.lower().startswith('lo'):
            level = 0
        else:
            try:
                level = int(token)
            except ValueError:
                level = None
        resolved = uw_plus_values.get((track.uw_name, track.plus_track_name, level)) if level is not None else None
        row = StatInput(stat_name=track_name, source_family='uw_plus', source_name=track.uw_name, value=resolved if resolved is not None else (0.0 if level == 0 else track.display_token), value_type='resolved_value' if resolved is not None or level == 0 else 'display_token', stage='account_state', provenance='IDS::UWs', notes='kb_uw_plus_track_resolved' if resolved is not None else ('kb_uw_plus_locked_level0' if level == 0 else 'runtime_surface_preserved_pending_uw_plus_lookup'))
        if level is not None:
            _set_row_field(row, 'destination_object_type', 'mechanic_param')
            uw_plus_slug = slug_text(track.uw_name).replace(' ', '_')
            plus_track_slug = slug_text(track.plus_track_name).replace(' ', '_')
            _set_row_field(row, 'destination_id', f'uw_plus.{uw_plus_slug}.{plus_track_slug}')
            _set_row_field(row, 'resolver_id', 'standard_scalar_param')
            _set_row_field(row, 'kb_mapped', True)
        _append(out, row)

    # Cards: only active preset cards contribute. Use exact base ladder rows and alias routing.
    active_cards = account_state.card_presets.get(card_preset, [])
    for card_name in active_cards:
        if card_name == 'Berserker' and not resolved_projection_state.berserker_damage_bonus:
            continue
        snap = account_state.cards_inventory.get(card_name)
        if snap is None or snap.level is None:
            continue
        ladder = card_ladders.get((card_name, snap.level))
        value = None
        if ladder is not None:
            try:
                value = float(ladder['raw_value'])
            except (ValueError, TypeError):
                value = None
        row = StatInput(stat_name=card_name, source_family='card', source_name=card_name, value=value if value is not None else snap.level, value_type='resolved_value' if value is not None else 'level', stage='loadout_resolved', preset_name=card_preset, provenance='IDS::Cards')
        card_id = (ladder or {}).get('card_id') if ladder else None
        destination = card_effect_targets.get(card_id or '')
        if card_id == 'FREE_UPGRADES':
            for target_id in ('free_attack_upgrade_chance_pct', 'free_defense_upgrade_chance_pct', 'free_utility_upgrade_chance_pct'):
                split_row = StatInput(**{field: getattr(row, field) for field in StatInput.__dataclass_fields__.keys()})
                bind_destination(split_row, ('canonical_stat', target_id), canonical_stats, note=f'kb_card_effect_registry_split_routed:{card_id}')
                _append(out, split_row)
            continue
        if destination is not None:
            bind_destination(row, destination, canonical_stats, note=f'kb_card_effect_registry_routed:{card_id}')
        else:
            fallback_destination = CARD_NAME_FALLBACK_DESTINATION.get(slug_text(card_name))
            if fallback_destination is not None:
                bind_destination(row, fallback_destination, canonical_stats, note='kb_card_name_fallback_routed')
            else:
                bind_alias_destination(row, card_name, alias_index, canonical_stats, note='kb_alias_routed_card')
        if row.destination_object_type == 'capability' and row.destination_id and row.destination_id.endswith('.enabled'):
            _set_row_field(row, 'value', True)
            _set_row_field(row, 'value_type', 'bool')
        if row.destination_id == 'tower_orb_count' and card_name == 'Extra Orb':
            _set_row_field(row, 'value', 1.0)
            _set_row_field(row, 'value_type', 'resolved_value')
            _set_row_field(row, 'notes', (row.notes or '') + ':extra_orb_card_count_bonus')
        _append(out, row)


    # Perks: run-scoped selected modifiers owned by KB perk registries.
    perk_lab_state = _perk_lab_state(account_state)
    projected_perks_enabled = resolved_projection_state.projected_perks or perk_preset_namespace_class != 'transient'
    selected_perks = _active_perk_selections(account_state, perk_preset) if perks_enabled and projected_perks_enabled else []
    for perk_id, requested_picks in selected_perks:
        perk_meta = perk_entities.get(perk_id, {})
        perk_name = str(perk_meta.get('perk_name') or perk_id)
        max_picks = int(perk_meta.get('max_picks') or 1)
        applied_picks = max(0, min(requested_picks, max_picks))
        effects = perk_effects.get(perk_id, [])
        if applied_picks <= 0:
            continue
        for effect in effects:
            operation = effect.get('operation', '').strip()
            raw_value = effect.get('effect_value', '').strip()
            target_stat_id = effect.get('target_stat_id', '').strip()
            effect_index = effect.get('effect_index', '').strip()
            value = _scaled_perk_value(
                perk_meta=perk_meta,
                perk_effect_meta=effect,
                perk_id=perk_id,
                operation=operation,
                raw_value=raw_value,
                picks=applied_picks,
                effect_index=effect_index,
                perk_lab_state=perk_lab_state,
            )
            value_type = _perk_value_type_for_operation(operation)
            row = StatInput(
                stat_name=f"{perk_name}::effect_{effect_index}",
                source_family='perk',
                source_name=perk_name,
                value=value,
                value_type=value_type,
                stage='run_selected',
                preset_name=canonical_output_perk_preset,
                provenance='KB::Perks',
                notes=f"perk_id={perk_id};picks={applied_picks};operation={operation};target={target_stat_id};standard_perk_bonus_mult={perk_lab_state['standard_bonus_multiplier']:.4f};tradeoff_bonus_mult={perk_lab_state['tradeoff_bonus_multiplier']:.4f}",
                contributor_id=f"perk::{perk_id}::effect_{effect_index}",
            )
            if target_stat_id == 'free_upgrade_chance_all':
                bind_perk_effect_destination(row, target_stat_id, canonical_stats, alias_index)
                _append(out, row)
                for split_target in ('free_attack_upgrade_chance_pct', 'free_defense_upgrade_chance_pct', 'free_utility_upgrade_chance_pct'):
                    split_row = StatInput(**{field: getattr(row, field) for field in StatInput.__dataclass_fields__.keys()})
                    bind_destination(split_row, ('canonical_stat', split_target), canonical_stats, note='kb_perk_effect_split_routed:free_upgrade_chance_all')
                    _append(out, split_row)
                continue
            if target_stat_id and target_stat_id != 'ranged_enemy_attack_distance':
                bind_perk_effect_destination(row, target_stat_id, canonical_stats, alias_index)
            _append(out, row)

    # Modules: parse selected modules and surface main stat/substats. Route substats by canonical aliases only.
    for slot_type, selection in account_state.module_presets.get(module_preset, {}).items():
        slot_state = account_state.module_system_state.get(slot_type)
        assist_level = slot_state.assist_level if slot_state else None
        lookup_eff = assist_efficiency_lookup.get(assist_level or -1)
        assist_multiplier_eff = (slot_state.multiplier_cap if slot_state and slot_state.multiplier_cap is not None else lookup_eff) if slot_state else lookup_eff
        assist_substat_eff = (slot_state.substat_cap if slot_state and slot_state.substat_cap is not None else lookup_eff) if slot_state else lookup_eff
        for role, mod_name in [('primary', selection.primary), ('assist', selection.assist)]:
            if not mod_name:
                continue
            mod = account_state.modules_inventory.get(mod_name)
            if mod is None:
                _append(out, StatInput(stat_name=f'{slot_type}::{role}', source_family='module', source_name=mod_name, value=None, value_type='missing_inventory', stage='loadout_resolved', preset_name=module_preset, provenance='IDS::Modules', notes='selected_module_missing_from_inventory_parse'))
                continue
            if mod.stat is not None:
                try:
                    main_value = float(mod.stat)
                except (ValueError, TypeError):
                    main_value = None
                if role == 'assist' and assist_level is not None and assist_multiplier_eff is not None:
                    full_assist_main = module_main_effect_multiplier(slot_type, mod.rarity, assist_level)
                    if full_assist_main is not None:
                        main_value = 1.0 + (full_assist_main - 1.0) * assist_multiplier_eff
                    elif main_value is not None:
                        main_value = 1.0 + (main_value - 1.0) * assist_multiplier_eff
                unique_rarity = normalize_module_unique_rarity(str(mod.rarity))
                if role == 'assist' and slot_state and getattr(slot_state, 'rarity_cap', None):
                    unique_rarity = normalize_module_unique_rarity(str(slot_state.rarity_cap))
                unique_lookup = module_unique_effect_values.get((slug_text(mod_name), unique_rarity))
                unique_value = unique_lookup[0] if unique_lookup is not None else main_value
                unique_measure = unique_lookup[1] if unique_lookup is not None else ''
                if role == 'assist' and unique_value is not None and assist_multiplier_eff is not None:
                    if unique_measure == 'count':
                        # Quantity-style assist unique contributions use slot rarity-cap values and remain integer-like.
                        # Do not multiply the count by assist efficiency; the weaker assist variant is represented by
                        # the assist rarity cap itself (e.g. Epic Orbital Augment -> 2 electrons).
                        unique_value = float(int(unique_value))
                    else:
                        unique_value = unique_value * assist_multiplier_eff
                unique_value_type = 'multiplier_display' if unique_measure == 'multiplier' else ('pct' if unique_measure == 'pct' else ('count' if unique_measure == 'count' else ('duration_seconds' if unique_measure == 'seconds' else ('resolved_value' if unique_measure in {'m', 'raw'} else ('multiplier_display' if unique_value is not None else 'raw_text')))))
                row = StatInput(stat_name=f'{mod_name}::main', source_family='module', source_name=mod_name, value=main_value if main_value is not None else mod.stat, value_type='multiplier_display' if main_value is not None else 'raw_text', stage='loadout_resolved', preset_name=module_preset, provenance='IDS::Modules', notes=(f'module_{role}_main_effect' + (f':assist_multiplier_eff={assist_multiplier_eff}' if role == 'assist' and assist_multiplier_eff is not None else '')))
                base_contributor = {
                    'cannon': 'module__cannon__damage__pct',
                    'armor': 'module__armor__health__pct',
                    'generator': 'module__generator__coins_kill_bonus__pct',
                    'core': 'module__core__ultimate_weapon_damage__pct',
                }.get(slot_type)
                unique_contributor = mapping_lookup_for_family_name(family_slug_index, 'module', mod_name)
                if base_contributor and main_value is not None:
                    bind_kb_fields(row, base_contributor, mapping_index, canonical_stats)
                    _set_row_field(row, 'notes', (row.notes or '') + ':kb_module_base_routed')
                    _set_row_field(row, 'contributor_id', _make_instance_contributor_id(row.contributor_id, source_name=mod_name, role=role))
                elif unique_contributor and main_value is not None:
                    bind_kb_fields(row, unique_contributor, mapping_index, canonical_stats)
                    _set_row_field(row, 'notes', (row.notes or '') + ':kb_module_unique_routed')
                    _set_row_field(row, 'contributor_id', _make_instance_contributor_id(row.contributor_id, source_name=mod_name, role=role))
                _append(out, row)
                if mod_name == 'Sharp Fortitude' and main_value is not None and role == 'primary':
                    for unique_contributor_id, note in [
                        ('module__armor__wall_health__pct', 'kb_manual_sharp_fortitude_wall_hp_routed'),
                        ('module__armor__wall_regen__pct', 'kb_manual_sharp_fortitude_wall_regen_routed'),
                    ]:
                        sf_row = StatInput(
                            stat_name=f'{mod_name}::unique',
                            source_family='module',
                            source_name=mod_name,
                            value=unique_value,
                            value_type=unique_value_type,
                            stage='loadout_resolved',
                            preset_name=module_preset,
                            provenance='IDS::Modules',
                            notes=f'module_{role}_unique_effect:{note}',
                        )
                        bind_kb_fields(sf_row, unique_contributor_id, mapping_index, canonical_stats)
                        _set_row_field(sf_row, 'contributor_id', _make_instance_contributor_id(sf_row.contributor_id, source_name=mod_name, role=role, sub_name='unique'))
                        _append(out, sf_row)
                if unique_contributor and main_value is not None and base_contributor and unique_contributor != base_contributor:
                    unique_row = StatInput(stat_name=f'{mod_name}::unique', source_family='module', source_name=mod_name, value=unique_value, value_type=unique_value_type, stage='loadout_resolved', preset_name=module_preset, provenance='IDS::Modules', notes=f'module_{role}_unique_effect')
                    bind_kb_fields(unique_row, unique_contributor, mapping_index, canonical_stats)
                    _set_row_field(unique_row, 'contributor_id', _make_instance_contributor_id(unique_row.contributor_id, source_name=mod_name, role=role, sub_name='unique'))
                    _append(out, unique_row)
                if mod_name == 'Singularity Harness' and unique_value is not None:
                    sh_row = StatInput(stat_name=f'{mod_name}::unique', source_family='module', source_name=mod_name, value=unique_value, value_type=unique_value_type, stage='loadout_resolved', preset_name=module_preset, provenance='IDS::Modules', notes=f'module_{role}_unique_effect:kb_manual_singularity_harness_bot_range_routed')
                    bind_destination(sh_row, ('mechanic_param', 'bot.global.range_bonus_m'), canonical_stats, note='kb_manual_singularity_harness_bot_range_routed')
                    _set_row_field(sh_row, 'contributor_id', _make_instance_contributor_id('module__generator__singularity_harness__bot_range_bonus_m', source_name=mod_name, role=role, sub_name='bot_range_bonus'))
                    _append(out, sh_row)
            for sub in mod.substats:
                numeric = None
                value_type = 'raw_text'
                display = str(sub.value or '').strip()
                token = str(sub.raw_token or '').strip()
                parse_failed = False
                if not display and not token:
                    continue
                try:
                    kb_unit = module_substat_units.get(sub.name, '')
                    substat_lookup_name = _module_substat_lookup_name(sub.name)
                    rarity_source = mod.rarity
                    if role == 'assist' and slot_state and getattr(slot_state, 'rarity_cap', None):
                        rarity_source = slot_state.rarity_cap
                    rarity_key = _canonical_module_rarity_label(rarity_source)
                    exact = module_substat_values.get((slot_type.lower(), substat_lookup_name, rarity_key))
                    exact_unit = exact[1] if exact is not None else ''
                    if role == 'assist' and exact is not None:
                        numeric = float(exact[0])
                        inferred_unit = kb_unit or exact_unit
                        if assist_substat_eff is not None:
                            numeric = numeric * assist_substat_eff
                        if inferred_unit == 'percent':
                            value_type = 'percent_display'
                        elif inferred_unit == 'multiplier':
                            value_type = 'multiplier_display'
                        else:
                            value_type = 'resolved_value'
                    elif '%' in display:
                        numeric = float(display.replace('+', '').replace('%', '').replace('?', '').strip())
                        if role == 'assist' and assist_substat_eff is not None:
                            numeric = numeric * assist_substat_eff
                        value_type = 'percent_display'
                    elif 'x' in display.lower():
                        numeric = float(display.replace('+', '').replace('x', '').replace('X', '').strip())
                        if role == 'assist' and assist_substat_eff is not None:
                            numeric = numeric * assist_substat_eff
                        value_type = 'multiplier_display'
                    else:
                        base = token or display
                        numeric = float(str(base).replace('+', '').replace('m', '').replace('s', '').replace('?', '').strip())
                        if role == 'assist' and assist_substat_eff is not None:
                            numeric = numeric * assist_substat_eff
                        inferred_unit = kb_unit or exact_unit
                        if inferred_unit == 'percent':
                            value_type = 'percent_display'
                        else:
                            value_type = 'resolved_value'
                except ValueError:
                    parse_failed = True
                notes = (f'module_{role}_substat' + (f':assist_substat_eff={assist_substat_eff}' if role == 'assist' and assist_substat_eff is not None else ''))
                parse_failed_marker = None
                if parse_failed and numeric is None:
                    token_context = token or display
                    sanitized_substat_name = slug_text(sub.name)
                    parse_failed_marker = f'module_substat_parse_failed:{sanitized_substat_name}:token={token_context}'
                    notes += f':{parse_failed_marker}'
                row = StatInput(stat_name=sub.name, source_family='module_substat', source_name=mod_name, value=numeric if numeric is not None else sub.value, value_type=value_type if numeric is not None else 'raw_text', stage='loadout_resolved', preset_name=module_preset, provenance='IDS::Modules', notes=notes)
                destination = MODULE_SUBSTAT_NAME_TO_DESTINATION.get(slug_text(sub.name))
                if destination is not None:
                    bind_destination(row, destination, canonical_stats, note=f'kb_exact_routed_module_substat_{role}')
                else:
                    bind_alias_destination(row, sub.name, alias_index, canonical_stats, note=f'kb_alias_routed_module_substat_{role}')
                if parse_failed_marker:
                    _set_row_field(row, 'notes', ((row.notes or '') + f':{parse_failed_marker}').strip(':'))
                if row.contributor_id:
                    _set_row_field(row, 'contributor_id', _make_instance_contributor_id(row.contributor_id, source_name=mod_name, role=role, sub_name=sub.name))
                _append(out, row)

    return [row for row in out if row_in_state_mode(row, state_mode)]
