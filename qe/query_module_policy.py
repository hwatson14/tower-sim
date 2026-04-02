"""Bounded QE owner for module policy and module-economy publication surfaces.

This module intentionally consolidates the module publication/policy surface area
so QE does not fragment into several tiny module-only publisher files.
"""

from __future__ import annotations

import csv
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable

from input.state_types import AccountState, ModuleSnapshot, ModuleSubstat, ModuleSystemState
from qe.models import StatRow

SUPPORTED_MODULE_RUNTIME_POLICY_INPUTS = {
    'module.farming.hours_per_day': {
        'surface_id': 'derived::module.runtime_profile.farming_hours_per_day',
        'unit': 'hours_per_day',
        'value_type': 'scalar',
    },
    'module.resource.gems_allocated_to_modules.per_week': {
        'surface_id': 'derived::module.resource_policy.gems_allocated_to_modules_per_week',
        'unit': 'gems_per_week',
        'value_type': 'per_week',
    },
    'module.missions.per_week': {
        'surface_id': 'planner.manual_policy.module.missions_per_week',
        'unit': 'missions_per_week',
        'value_type': 'per_week',
    },
}
MODULE_LAB_VALUE_MODELS = {
    'Reroll Shards': {
        'surface_id': 'derived::module.lab.reroll_shards_bonus',
        'unit': 'shards',
        'value_type': 'scalar',
        'formula': lambda level: float(level),
    },
    'Common Drop Chance': {
        'surface_id': 'derived::module.lab.common_drop_chance_bonus_pct',
        'unit': 'pct',
        'value_type': 'scalar',
        'formula': lambda level: float(level) * 0.1,
    },
    'Rare Drop Chance': {
        'surface_id': 'derived::module.lab.rare_drop_chance_bonus_pct',
        'unit': 'pct',
        'value_type': 'scalar',
        'formula': lambda level: float(level) * 0.1,
    },
    'Daily Mission Shards': {
        'surface_id': 'derived::module.lab.daily_mission_shards_bonus',
        'unit': 'shards_per_mission',
        'value_type': 'scalar',
        'formula': lambda level: float(level),
    },
    'Shatter Shards': {
        'surface_id': 'derived::module.lab.shatter_shards_bonus_pct',
        'unit': 'pct',
        'value_type': 'scalar',
        'formula': lambda level: float(level) * 20.0,
    },
}
MODULE_DROP_ECONOMY_INPUT_MAP = {
    'module.runtime.tier_for_drop_tables': {
        'surface_id': 'derived::module.runtime_profile.farming_tier',
        'unit': 'tier',
    },
    'module.labs.reroll_shards_bonus': {
        'surface_id': 'derived::module.lab.reroll_shards_bonus',
        'unit': 'shards',
    },
    'module.labs.common_drop_chance_bonus_pct': {
        'surface_id': 'derived::module.lab.common_drop_chance_bonus_pct',
        'unit': 'pct',
    },
    'module.labs.rare_drop_chance_bonus_pct': {
        'surface_id': 'derived::module.lab.rare_drop_chance_bonus_pct',
        'unit': 'pct',
    },
    'module.labs.daily_mission_shards_bonus': {
        'surface_id': 'derived::module.lab.daily_mission_shards_bonus',
        'unit': 'shards_per_mission',
    },
}
REROLL_SHARDS_BY_TIER = {
    1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0, 5: 6.0, 6: 8.0, 7: 12.0, 8: 18.0, 9: 25.0,
    10: 32.0, 11: 40.0, 12: 45.0, 13: 50.0, 14: 55.0, 15: 60.0, 16: 65.0, 17: 70.0, 18: 75.0,
}
BASE_DAILY_MISSION_SHARDS_BY_TIER = {
    1: 0.0, 2: 3.0, 3: 5.0, 4: 8.0, 5: 12.0, 6: 15.0, 7: 20.0, 8: 25.0, 9: 30.0,
    10: 34.0, 11: 38.0, 12: 42.0, 13: 48.0, 14: 55.0, 15: 60.0, 16: 65.0, 17: 70.0,
    18: 75.0, 19: 80.0, 20: 85.0, 21: 90.0,
}
MODULE_DRAW_POLICY_ROWS = (
    ('derived::module.draw_policy.common_rate_pct', 68.5, 'pct', 'scalar', 'Wiki-backed common module draw rate.'),
    ('derived::module.draw_policy.rare_rate_pct', 29.0, 'pct', 'scalar', 'Wiki-backed rare module draw rate.'),
    ('derived::module.draw_policy.epic_rate_pct', 2.5, 'pct', 'scalar', 'Wiki-backed epic module draw rate.'),
    ('derived::module.draw_policy.epic_pity_draws', 150.0, 'draws', 'scalar', 'Wiki-backed epic pity threshold for module draws.'),
    ('derived::module.draw_policy.ten_pull_minimum_rare', 1.0, 'rare_per_ten_pull', 'scalar', 'Wiki-backed minimum of one rare in every 10-pull.'),
    ('derived::module.draw_policy.gem_cost_per_draw', 20.0, 'gems', 'scalar', 'Wiki-backed module gem cost per single draw.'),
    ('derived::module.draw_policy.epic_draw_immediate_shard_value', 0.0, 'shards', 'scalar', 'KB package-rule epic draw immediate shard value: retained epics contribute zero immediate shards.'),
    ('derived::module.draw_policy.ten_pull_ev_multiplier', 1.0, 'multiplier', 'scalar', 'KB package-rule ten-pull EV multiplier: a 10-pull is modeled as ten independent singles for EV.'),
)


def supported_module_runtime_policy_input_ids() -> set[str]:
    return set(SUPPORTED_MODULE_RUNTIME_POLICY_INPUTS)


def published_module_runtime_policy_surface_ids() -> set[str]:
    return {row['surface_id'] for row in SUPPORTED_MODULE_RUNTIME_POLICY_INPUTS.values()}


def _manual_input_is_set(entry: Dict[str, Any]) -> bool:
    if bool(entry.get('is_set', False)):
        return True
    return isinstance(entry.get('value'), (int, float))


def _publish_surface(rows: Dict[str, StatRow], *, surface_id: str, value: float, value_type: str, unit: str, notes: str, contributors: list[dict], schema: dict) -> None:
    existing = rows.get(surface_id)
    if existing is not None:
        raise ValueError(f'Module runtime/policy publication collision for {surface_id}')
    rows[surface_id] = StatRow(
        stat_name=surface_id,
        final_value=value,
        value_type=value_type,
        source_count=len(contributors),
        status='resolved',
        notes=notes,
        contributors=contributors,
        schema=schema | {'unit': unit},
    )


def _require(rows: Dict[str, StatRow], surface_id: str) -> float:
    row = rows.get(surface_id)
    if row is None:
        raise ValueError(f'missing required upstream surface: {surface_id}')
    return float(row.final_value)


def _prepopulate_drop_economy_upstream_surfaces(
    rows: Dict[str, StatRow],
    manual_advisory_inputs: Dict[str, Dict[str, Any]] | None = None,
) -> None:
    manual_inputs = manual_advisory_inputs or {}
    for input_id, spec in MODULE_DROP_ECONOMY_INPUT_MAP.items():
        surface_id = spec['surface_id']
        if surface_id in rows:
            continue
        entry = manual_inputs.get(input_id)
        if entry is None or not entry.get('is_set', False):
            continue
        try:
            value = float(entry['value'])
        except (TypeError, ValueError, KeyError):
            continue
        rows[surface_id] = StatRow(
            stat_name=surface_id,
            final_value=value,
            value_type='scalar',
            source_count=1,
            status='resolved',
            notes=f'Pre-populated from the input-owned manual_advisory_inputs surface for {input_id}.',
            contributors=[{'source_class': 'manual_input', 'input_id': input_id, 'value': value, 'unit': spec['unit']}],
            schema={'source_alignment': 'Inputs', 'unit': spec['unit'], 'publisher': 'query_module_policy'},
        )


def publish_module_runtime_policy_surfaces(
    rows: Dict[str, StatRow],
    manual_advisory_inputs: Dict[str, Dict[str, Any]] | None = None,
) -> None:
    manual_inputs = manual_advisory_inputs or {}
    for input_id, spec in SUPPORTED_MODULE_RUNTIME_POLICY_INPUTS.items():
        entry = manual_inputs.get(input_id)
        if entry is None or not _manual_input_is_set(entry):
            continue
        try:
            value = float(entry.get('value'))
        except (TypeError, ValueError):
            continue
        _publish_surface(
            rows,
            surface_id=spec['surface_id'],
            value=value,
            value_type=spec['value_type'],
            unit=spec['unit'],
            notes='Derived from the input-owned manual_advisory_inputs surface.',
            contributors=[{
                'surface_id': spec['surface_id'],
                'source_class': 'manual_input',
                'input_id': input_id,
                'value': value,
                'unit': spec['unit'],
                'trust_label': entry.get('trust_label', 'accepted_model'),
                'consumer_scope': entry.get('consumer_scope', []),
                'source_alignment': 'Inputs',
            }],
            schema={
                'source_alignment': 'Inputs',
                'input_id': input_id,
                'externalized': True,
                'publisher': 'query_module_policy',
                'is_set': True,
            },
        )


def publish_module_draw_policy_surfaces(rows: Dict[str, StatRow]) -> None:
    for surface_id, value, unit, value_type, notes in MODULE_DRAW_POLICY_ROWS:
        _publish_surface(
            rows,
            surface_id=surface_id,
            value=value,
            value_type=value_type,
            unit=unit,
            notes=notes,
            contributors=[{'source_class': 'wiki_truth', 'value': value, 'unit': unit}],
            schema={'source_alignment': 'Wiki', 'publisher': 'query_module_policy'},
        )


def publish_module_lab_policy_surfaces(rows: Dict[str, StatRow], account_state_labs: Dict[str, Any]) -> None:
    if not isinstance(account_state_labs, dict):
        raise ValueError('account_state_labs dict required')

    for lab_name, spec in MODULE_LAB_VALUE_MODELS.items():
        raw_level = account_state_labs.get(lab_name, 0)
        if raw_level in (None, ''):
            continue
        try:
            level = int(raw_level)
        except (TypeError, ValueError):
            raise ValueError(f'invalid level for lab {lab_name}: {raw_level}')
        value = spec['formula'](level)
        _publish_surface(
            rows,
            surface_id=spec['surface_id'],
            value=value,
            value_type=spec['value_type'],
            unit=spec['unit'],
            notes='QE-routed module lab value derived from account_state.labs using wiki-backed level semantics.',
            contributors=[{
                'source_class': 'account_state_lab',
                'lab_name': lab_name,
                'level': level,
                'value': value,
                'unit': spec['unit'],
                'source_alignment': 'AccountState+Wiki',
            }],
            schema={'source_alignment': 'AccountState+Wiki', 'publisher': 'query_module_policy', 'lab_name': lab_name, 'level': level},
        )


def publish_module_drop_economy_surfaces(
    rows: Dict[str, StatRow],
    manual_advisory_inputs: Dict[str, Dict[str, Any]] | None = None,
) -> None:
    _prepopulate_drop_economy_upstream_surfaces(rows, manual_advisory_inputs)
    farming_tier = int(_require(rows, 'derived::module.runtime_profile.farming_tier'))
    if farming_tier not in REROLL_SHARDS_BY_TIER:
        raise ValueError(f'unsupported farming tier for module drop tables: {farming_tier}')

    reroll_lab_bonus = rows.get('derived::module.lab.reroll_shards_bonus')
    common_lab_bonus = rows.get('derived::module.lab.common_drop_chance_bonus_pct')
    rare_lab_bonus = rows.get('derived::module.lab.rare_drop_chance_bonus_pct')
    mission_lab_bonus = rows.get('derived::module.lab.daily_mission_shards_bonus')
    shatter_bonus = rows.get('derived::module.lab.shatter_shards_bonus_pct')

    reroll_bonus = float(reroll_lab_bonus.final_value) if reroll_lab_bonus else 0.0
    common_bonus = float(common_lab_bonus.final_value) if common_lab_bonus else 0.0
    rare_bonus = float(rare_lab_bonus.final_value) if rare_lab_bonus else 0.0
    mission_bonus = float(mission_lab_bonus.final_value) if mission_lab_bonus else 0.0
    shatter_mult = 1.0 + ((float(shatter_bonus.final_value) if shatter_bonus else 0.0) / 100.0)

    _publish_surface(
        rows, surface_id='derived::module.drop_policy.reroll_shard_drop_chance_pct',
        value=15.0, unit='pct', value_type='scalar',
        notes='Wiki-backed base boss reroll shard drop chance.',
        contributors=[{'source_class': 'wiki_truth', 'value': 15.0, 'unit': 'pct'}],
        schema={'source_alignment': 'Wiki', 'publisher': 'query_module_policy'},
    )
    _publish_surface(
        rows, surface_id='derived::module.drop_policy.reroll_shards_per_boss',
        value=REROLL_SHARDS_BY_TIER[farming_tier] + reroll_bonus, unit='shards', value_type='scalar',
        notes='Wiki-backed tier reroll shard amount per successful boss drop plus QE-routed lab bonus.',
        contributors=[{'source_class': 'wiki_truth', 'value': REROLL_SHARDS_BY_TIER[farming_tier], 'unit': 'shards'}],
        schema={'source_alignment': 'Wiki+QE', 'publisher': 'query_module_policy', 'tier': farming_tier},
    )
    _publish_surface(
        rows, surface_id='derived::module.drop_policy.common_module_drop_chance_pct',
        value=2.0 + common_bonus, unit='pct', value_type='scalar',
        notes='Wiki-backed base common module boss drop chance plus QE-routed lab bonus.',
        contributors=[{'source_class': 'wiki_truth', 'value': 2.0, 'unit': 'pct'}],
        schema={'source_alignment': 'Wiki+QE', 'publisher': 'query_module_policy'},
    )
    _publish_surface(
        rows, surface_id='derived::module.drop_policy.rare_module_drop_chance_pct',
        value=0.5 + rare_bonus, unit='pct', value_type='scalar',
        notes='Wiki-backed base rare module boss drop chance plus QE-routed lab bonus.',
        contributors=[{'source_class': 'wiki_truth', 'value': 0.5, 'unit': 'pct'}],
        schema={'source_alignment': 'Wiki+QE', 'publisher': 'query_module_policy'},
    )
    _publish_surface(
        rows, surface_id='derived::module.shatter_policy.common_module_shards',
        value=5.0 * shatter_mult, unit='shards', value_type='scalar',
        notes='Wiki-backed common module shatter shards with QE-routed shatter-shards lab applied.',
        contributors=[{'source_class': 'wiki_truth', 'value': 5.0, 'unit': 'shards'}],
        schema={'source_alignment': 'Wiki+QE', 'publisher': 'query_module_policy'},
    )
    _publish_surface(
        rows, surface_id='derived::module.shatter_policy.rare_module_shards',
        value=10.0 * shatter_mult, unit='shards', value_type='scalar',
        notes='Wiki-backed rare module shatter shards with QE-routed shatter-shards lab applied.',
        contributors=[{'source_class': 'wiki_truth', 'value': 10.0, 'unit': 'shards'}],
        schema={'source_alignment': 'Wiki+QE', 'publisher': 'query_module_policy'},
    )
    _publish_surface(
        rows, surface_id='derived::module.mission_policy.daily_mission_shards_bonus',
        value=mission_bonus, unit='shards_per_mission', value_type='scalar',
        notes='QE-routed daily mission shard bonus lab value. Base mission shard reward remains unresolved.',
        contributors=[{'source_class': 'account_state_lab', 'value': mission_bonus, 'unit': 'shards_per_mission'}],
        schema={'source_alignment': 'QE', 'publisher': 'query_module_policy', 'base_mission_shards_unresolved': True},
    )

    expected_shatter_equiv = (
        (2.0 + common_bonus) / 100.0 * (5.0 * shatter_mult)
        + (0.5 + rare_bonus) / 100.0 * (10.0 * shatter_mult)
    )
    _publish_surface(
        rows, surface_id='derived::module.drop_policy.expected_shatter_equivalent_shards_per_boss',
        value=expected_shatter_equiv, unit='shards_per_boss', value_type='scalar',
        notes='Computed shatter-equivalent expected shard value of boss module drops assuming all dropped common/rare modules are shattered.',
        contributors=[{'source_class': 'computed_from_wiki_truth', 'value': expected_shatter_equiv, 'unit': 'shards_per_boss'}],
        schema={'source_alignment': 'WikiDerived+QE', 'publisher': 'query_module_policy', 'assumption': 'all_dropped_common_and_rare_modules_shattered'},
    )


def publish_module_mission_economy_surfaces(rows: Dict[str, StatRow]) -> None:
    highest_tier = int(_require(rows, 'derived::module.runtime_profile.highest_tier_unlocked'))
    if highest_tier not in BASE_DAILY_MISSION_SHARDS_BY_TIER:
        raise ValueError(f'unsupported highest tier unlocked for mission economy: {highest_tier}')

    mission_bonus_row = rows.get('derived::module.mission_policy.daily_mission_shards_bonus')
    mission_bonus = float(mission_bonus_row.final_value) if mission_bonus_row else 0.0
    base_shards = BASE_DAILY_MISSION_SHARDS_BY_TIER[highest_tier]
    total_per_mission = base_shards + mission_bonus

    _publish_surface(
        rows, surface_id='derived::module.mission_policy.base_daily_mission_shards',
        value=base_shards, unit='shards_per_mission', value_type='scalar',
        notes='Wiki-backed base daily mission shard reward by highest tier unlocked.',
        contributors=[{'source_class': 'wiki_truth', 'value': base_shards, 'unit': 'shards_per_mission'}],
        schema={'source_alignment': 'Wiki', 'publisher': 'query_module_policy', 'highest_tier_unlocked': highest_tier},
    )
    _publish_surface(
        rows, surface_id='derived::module.mission_policy.total_daily_mission_shards',
        value=total_per_mission, unit='shards_per_mission', value_type='scalar',
        notes='Total daily mission shard reward per mission: wiki-backed base plus QE-routed lab bonus.',
        contributors=[{'source_class': 'computed_from_wiki_and_qe', 'value': total_per_mission, 'unit': 'shards_per_mission'}],
        schema={'source_alignment': 'Wiki+QE', 'publisher': 'query_module_policy', 'highest_tier_unlocked': highest_tier},
    )


def module_runtime_policy_surface_contract_snapshot() -> Dict[str, Any]:
    return {
        'supported_manual_input_ids': sorted(supported_module_runtime_policy_input_ids()),
        'published_surface_ids': sorted(published_module_runtime_policy_surface_ids()),
        'supported_inputs': {
            input_id: {
                'surface_id': spec['surface_id'],
                'unit': spec['unit'],
                'value_type': spec['value_type'],
            }
            for input_id, spec in sorted(SUPPORTED_MODULE_RUNTIME_POLICY_INPUTS.items())
        },
        'planner_manual_inputs_retained': ['module.planner.horizon_days', 'module.missions.per_week'],
    }


ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / 'kb'
MODULE_SUBSTATS_TABLE_PATH = KB / 'modules' / 'tables' / 'module-substats.csv'
MODULE_UNIQUE_EFFECTS_TABLE_PATH = KB / 'modules' / 'tables' / 'module-unique-effects.csv'
MODULE_UNIQUE_RUNTIME_CATALOG_PATH = KB / 'modules' / 'contracts' / 'module-unique-runtime-catalog.csv'
MODULE_MAIN_EFFECT_BASES_PATH = KB / 'modules' / 'tables' / 'module-main-effect-bases.csv'
MODULE_MAIN_EFFECT_STEPS_PATH = KB / 'modules' / 'sources' / 'raw' / 'effective-paths' / 'sheet-exports' / 'module-base-stat-values.csv'
ASSIST_STONE_LEVELS_PATH = KB / 'modules' / 'tables' / 'assist-stone-levels.csv'
MODULE_DEFINED_NAMES_PATH = KB / 'modules' / 'sources' / 'raw' / 'effective-paths' / 'defined-names' / 'module-defined-names.csv'
MODULE_WIKI_BASELINES_PATH = KB / 'modules' / 'sources' / 'wiki-modules-and-submodules.md'

_MODULE_MAIN_LABELS = {
    'cannon': 'Damage',
    'armor': 'Health',
    'generator': 'Coins / Kill Bonus',
    'core': 'Ultimate Weapon Damage',
}

_MODULE_RARITY_ORDER = {
    'Common': 0,
    'Rare': 1,
    'Epic': 2,
    'Legendary': 3,
    'Mythic': 4,
    'Ancestral': 5,
}

_MODULE_RARITY_KEY_MAP = {
    'Common': 'common',
    'Rare': 'rare',
    'Epic': 'epic',
    'Legendary': 'legendary',
    'Mythic': 'mythic',
    'Ancestral': 'ancestral',
}

_MODULE_SUBSTAT_ALIASES = {
    'Defense %': 'Defense',
    'Critical Factor': 'Crit Factor',
    'MultiShot Chance': 'Multishot Chance',
}


@dataclass(frozen=True)
class ModuleCardEffectSlot:
    slot_index: int
    state: str
    unlock_level: int
    rarity_key: str | None
    rarity_text: str | None
    value_text: str | None
    label_text: str | None


@dataclass(frozen=True)
class ModuleCardUniqueText:
    prefix_text: str
    value_text: str | None
    suffix_text: str


@dataclass(frozen=True)
class ModuleCardPayload:
    module_name: str
    slot_type: str
    role: str
    rarity_text: str
    rarity_key: str | None
    stars: int
    displayed_level: int | None
    displayed_level_cap: int | None
    level_text: str
    role_bar_label_text: str
    role_bar_detail_text: str
    main_value_text: str
    main_label_text: str
    unique_value_text: str | None
    unique_measure: str | None
    unique_text: ModuleCardUniqueText | None
    effect_slots: tuple[ModuleCardEffectSlot, ...]


def _slug_text(value: str) -> str:
    return ''.join(ch.lower() if ch.isalnum() else '_' for ch in value).strip('_')


def _trim_decimal_string(text: str) -> str:
    return text.rstrip('0').rstrip('.') if '.' in text else text


def _normalize_module_substat_name(value: object) -> str:
    text = str(value or '').strip()
    return _MODULE_SUBSTAT_ALIASES.get(text, text)


def _canonical_rarity_label(rarity: object) -> str | None:
    text = str(rarity or '').strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered.startswith('ancestral'):
        return 'Ancestral'
    if lowered.startswith('mythic'):
        return 'Mythic'
    if lowered.startswith('legendary'):
        return 'Legendary'
    if lowered.startswith('epic'):
        return 'Epic'
    if lowered.startswith('rare'):
        return 'Rare'
    if lowered.startswith('common'):
        return 'Common'
    return text.title()


def _cap_rarity(rarity: object, cap: object) -> str | None:
    rarity_label = _canonical_rarity_label(rarity)
    cap_label = _canonical_rarity_label(cap)
    rarity_rank = _MODULE_RARITY_ORDER.get(rarity_label) if rarity_label else None
    cap_rank = _MODULE_RARITY_ORDER.get(cap_label) if cap_label else None
    if rarity_rank is None and cap_rank is None:
        return None
    if rarity_rank is None:
        return cap_label
    if cap_rank is None:
        return rarity_label
    rank = min(rarity_rank, cap_rank)
    for label, candidate in _MODULE_RARITY_ORDER.items():
        if candidate == rank:
            return label
    return rarity_label


def normalize_module_unique_rarity(rarity: str | None) -> str:
    r = str(rarity or '').strip().lower()
    if r.startswith('epic'):
        return 'epic'
    if r.startswith('legendary'):
        return 'legendary'
    if r.startswith('mythic'):
        return 'mythic'
    if r.startswith('ancestral'):
        return 'ancestral'
    if r.startswith('rare'):
        return 'rare'
    if r.startswith('common'):
        return 'common'
    return r


def normalize_module_base_rarity(rarity: str | None) -> tuple[str | None, int]:
    value = str(rarity or '').strip()
    if not value:
        return None, 0
    match = re.match(r'^(Ancestral)(?:\s+(\d)\*)?$', value)
    if match:
        return 'Ancestral', int(match.group(2) or 0)
    return value, 0


@lru_cache(maxsize=1)
def load_module_substat_values() -> dict[tuple[str, str, str], tuple[float, str]]:
    out: dict[tuple[str, str, str], tuple[float, str]] = {}
    if not MODULE_SUBSTATS_TABLE_PATH.exists():
        return out
    with MODULE_SUBSTATS_TABLE_PATH.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            slot = str(row.get('slot') or '').strip().lower()
            substat = _normalize_module_substat_name(row.get('substat'))
            rarity = _canonical_rarity_label(row.get('rarity'))
            try:
                value = float(row.get('value'))
            except (TypeError, ValueError):
                continue
            unit = str(row.get('unit') or '').strip().lower()
            if slot and substat and rarity:
                out[(slot, substat, rarity)] = (value, unit)
    return out


@lru_cache(maxsize=1)
def _load_module_substat_lookup() -> dict[tuple[str, str], list[dict[str, object]]]:
    lookup: dict[tuple[str, str], list[dict[str, object]]] = {}
    for (slot, substat, rarity), (value, unit) in load_module_substat_values().items():
        lookup.setdefault((slot, substat), []).append({
            'rarity': rarity,
            'value': value,
            'unit': unit,
        })
    for key in lookup:
        lookup[key].sort(key=lambda row: _MODULE_RARITY_ORDER.get(str(row['rarity']), 999))
    return lookup


@lru_cache(maxsize=1)
def _load_module_main_effect_bases() -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    if not MODULE_MAIN_EFFECT_BASES_PATH.exists():
        return out
    with MODULE_MAIN_EFFECT_BASES_PATH.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            rarity = str(row.get('rarity') or '').strip()
            if not rarity:
                continue
            vals: dict[str, float] = {}
            for slot in ('cannon', 'armor', 'generator', 'core'):
                try:
                    vals[slot] = float(row.get(f'{slot}_base'))
                except (TypeError, ValueError):
                    continue
            out[rarity] = vals
    return out


@lru_cache(maxsize=1)
def _load_module_main_effect_steps() -> dict[str, list[tuple[int, float]]]:
    out: dict[str, list[tuple[int, float]]] = {'cannon': [], 'armor': [], 'generator': [], 'core': []}
    if not MODULE_MAIN_EFFECT_STEPS_PATH.exists():
        return out
    with MODULE_MAIN_EFFECT_STEPS_PATH.open(newline='', encoding='utf-8') as handle:
        rows = list(csv.reader(handle))
    capture = False
    for row in rows:
        if not row:
            continue
        key = str(row[0]).strip()
        if key == 'Increase / lvl':
            capture = True
            continue
        if not capture:
            continue
        if key == '300.0':
            break
        try:
            level = int(float(key))
        except (TypeError, ValueError):
            continue
        for idx, slot in enumerate(('cannon', 'armor', 'generator', 'core'), start=1):
            try:
                inc = float(row[idx])
            except (TypeError, ValueError):
                continue
            out[slot].append((level, inc))
    return out


def module_main_effect_multiplier(slot_type: str, rarity: str | None, level: int | None) -> float | None:
    base_rarity, stars = normalize_module_base_rarity(rarity)
    if not base_rarity or level is None:
        return None
    bases = _load_module_main_effect_bases().get(base_rarity)
    if not bases:
        return None
    try:
        base = float(bases[slot_type])
    except Exception:
        return None
    step_rows = _load_module_main_effect_steps().get(slot_type, [])
    total = base
    next_levels = [lvl for lvl, _ in step_rows[1:]] + [300]
    for (start, inc), nxt in zip(step_rows, next_levels):
        if level <= start:
            continue
        total += (min(level, nxt) - start) * inc
    star_factor = 1.0 + 0.04 * stars
    return round(total * star_factor + 1.0, 3)


@lru_cache(maxsize=1)
def load_module_unique_effect_values() -> dict[tuple[str, str], tuple[float, str]]:
    out: dict[tuple[str, str], tuple[float, str]] = {}
    if not MODULE_UNIQUE_EFFECTS_TABLE_PATH.exists():
        return out
    rarity_columns = ('epic', 'legendary', 'mythic', 'ancestral')
    with MODULE_UNIQUE_EFFECTS_TABLE_PATH.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            module_slug = _slug_text(str(row.get('module') or '').strip())
            measure = str(row.get('measure') or '').strip().lower()
            if not module_slug:
                continue
            for rarity in rarity_columns:
                try:
                    value = float(row.get(rarity))
                except (TypeError, ValueError):
                    continue
                out[(module_slug, rarity)] = (value, measure)
    return out


@lru_cache(maxsize=1)
def load_assist_efficiency_lookup() -> dict[int, float]:
    out: dict[int, float] = {}
    if not ASSIST_STONE_LEVELS_PATH.exists():
        return out
    with ASSIST_STONE_LEVELS_PATH.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            try:
                level = int(row.get('stone_level'))
                frac = float(row.get('assist_efficiency_frac'))
            except (TypeError, ValueError):
                continue
            out[level] = frac
    return out


@lru_cache(maxsize=1)
def _load_module_unique_runtime_catalog() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    if not MODULE_UNIQUE_RUNTIME_CATALOG_PATH.exists():
        return out
    with MODULE_UNIQUE_RUNTIME_CATALOG_PATH.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            slug = _slug_text(str(row.get('module_name') or '').strip())
            if slug:
                out[slug] = dict(row)
    return out


@lru_cache(maxsize=1)
def module_substat_unlock_levels() -> tuple[int, ...]:
    if not MODULE_DEFINED_NAMES_PATH.exists():
        return (1, 1, 41, 101, 141, 161, 201, 241)
    with MODULE_DEFINED_NAMES_PATH.open(newline='', encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            if str(row.get('defined_name') or '').strip() != 'IDS_MOD_SUBSTATS_HELPER':
                continue
            formula = str(row.get('formula_or_ref') or '')
            matches = [int(value) for value in re.findall(r'level>=([0-9]+)', formula)]
            if not matches:
                break
            thresholds = tuple([1, 1] + sorted(matches))
            if len(thresholds) == 8:
                return thresholds
            break
    return (1, 1, 41, 101, 141, 161, 201, 241)


@lru_cache(maxsize=1)
def _load_module_level_caps() -> dict[str, int]:
    caps: dict[str, int] = {}
    if not MODULE_WIKI_BASELINES_PATH.exists():
        return caps
    pattern = re.compile(r'^-\s+(Rare\+|Rare|Epic\+|Epic|Legendary\+|Legendary|Mythic\+|Mythic|Ancestral|[1-5]\*)\s+([0-9]+)\s*$')
    for line in MODULE_WIKI_BASELINES_PATH.read_text(encoding='utf-8').splitlines():
        match = pattern.match(line.strip())
        if match:
            caps[match.group(1)] = int(match.group(2))
    return caps


def module_level_cap(rarity: str | None) -> int | None:
    caps = _load_module_level_caps()
    base_rarity, stars = normalize_module_base_rarity(rarity)
    if base_rarity == 'Ancestral' and stars > 0:
        return caps.get(f'{stars}*')
    if base_rarity is None:
        return None
    return caps.get(base_rarity)


def _parse_token_value(display: object, raw_token: object = None) -> tuple[float | None, str]:
    raw_text = str(raw_token or '').strip()
    if raw_text:
        try:
            return float(raw_text), _parse_token_value(display, None)[1]
        except ValueError:
            pass
    text = str(display or '').strip()
    if not text:
        return None, ''
    match = re.match(r'^([+-]?[0-9]+(?:\.[0-9]+)?)([^0-9.]*)$', text.replace('+', '', 1).strip())
    if not match:
        cleaned = text.replace('+', '').strip()
        try:
            return float(cleaned), ''
        except ValueError:
            return None, ''
    try:
        return float(match.group(1)), match.group(2).strip()
    except ValueError:
        return None, match.group(2).strip()


def _format_token_value(value: float | None, suffix: str, *, signed_default: bool = True, fixed_decimals: int | None = None) -> str:
    if value is None:
        return ''
    if fixed_decimals is None:
        number = _trim_decimal_string(f'{value:.4f}')
    else:
        number = f'{value:.{fixed_decimals}f}'
    if suffix == '%':
        sign = '+' if value >= 0 else ''
        return f'{sign}{number}%'
    if suffix == 'x':
        sign = '+' if value >= 0 else ''
        return f'{sign}{number}x'
    if suffix in {'s', 'm', '?'}:
        sign = '+' if value >= 0 else ''
        return f'{sign}{number}{suffix}'
    if signed_default:
        sign = '+' if value >= 0 else ''
        return f'{sign}{number}'
    return number


def _format_main_value_text(value: float | None, raw_text: object = None) -> str:
    if value is None:
        return f"x{str(raw_text or '').strip()}" if str(raw_text or '').strip() else ''
    return f"x{_trim_decimal_string(f'{value:.4f}') }"


def _format_level_text(*, role: str, displayed_level: int | None, displayed_level_cap: int | None) -> str:
    if displayed_level is None:
        return ''
    if role == 'assist' or displayed_level_cap is None:
        return f'Lv. {displayed_level}'
    return f'Lv. {displayed_level} / {displayed_level_cap}'


def _format_assist_summary(slot_state: ModuleSystemState | None) -> str:
    if slot_state is None:
        return ''
    rarity_text = _canonical_rarity_label(slot_state.rarity_cap) or str(slot_state.rarity_cap or '').strip() or 'n/a'
    main_eff = slot_state.multiplier_cap
    sub_eff = slot_state.substat_cap
    main_text = 'n/a' if main_eff is None else f'{main_eff:.2f}x'
    sub_text = 'n/a' if sub_eff is None else f'{sub_eff:.2f}x'
    return f'{rarity_text} | Main {main_text} | Substats {sub_text}'


def _infer_substat_rarity(slot_type: str, sub: ModuleSubstat, *, role: str, slot_state: ModuleSystemState | None) -> str | None:
    name = _normalize_module_substat_name(sub.name)
    if not name:
        return None
    entries = _load_module_substat_lookup().get((slot_type.strip().lower(), name))
    if not entries:
        return _cap_rarity(None, slot_state.rarity_cap if slot_state else None) if role == 'assist' else None
    raw_value, _ = _parse_token_value(sub.value, sub.raw_token)
    matched_rarity = None
    if raw_value is not None:
        for entry in entries:
            candidate = float(entry['value'])
            unit = str(entry['unit'])
            comparisons = [candidate]
            if unit == 'percent':
                comparisons.append(candidate / 100.0)
            if any(abs(raw_value - probe) <= 1e-9 for probe in comparisons):
                matched_rarity = str(entry['rarity'])
                break
    if matched_rarity is None and entries:
        matched_rarity = str(entries[-1]['rarity'])
    if role == 'assist':
        return _cap_rarity(matched_rarity, slot_state.rarity_cap if slot_state else None) or matched_rarity
    return matched_rarity


def _format_unique_value_text(value: float | None, measure: str | None) -> str | None:
    if value is None:
        return None
    measure = str(measure or '').strip().lower()
    if measure == 'count':
        return str(int(value))
    if measure == 'pct':
        return f'{_trim_decimal_string(f"{value:.4f}")}%'
    if measure == 'multiplier':
        return f'x{_trim_decimal_string(f"{value:.4f}")}'
    if measure == 'seconds':
        return f'{_trim_decimal_string(f"{value:.4f}")}s'
    if measure == 'm':
        return f'{_trim_decimal_string(f"{value:.4f}")}m'
    return _trim_decimal_string(f'{value:.4f}')


def _build_unique_text(module_name: str, value_text: str | None, measure: str | None) -> ModuleCardUniqueText | None:
    behavior = (_load_module_unique_runtime_catalog().get(_slug_text(module_name), {}) or {}).get('behavior') or ''
    behavior = str(behavior).strip()
    if not behavior and not value_text:
        return None
    if not behavior:
        return ModuleCardUniqueText(prefix_text='', value_text=value_text, suffix_text='')
    if not value_text:
        return ModuleCardUniqueText(prefix_text=behavior, value_text=None, suffix_text='')
    patterns = [
        r'listed value',
        r'listed percent',
        r'listed chance',
        r'listed radius',
        r'listed cooldown',
        r'listed amount',
        r'listed',
    ]
    for pattern in patterns:
        match = re.search(pattern, behavior, flags=re.IGNORECASE)
        if match:
            return ModuleCardUniqueText(
                prefix_text=behavior[:match.start()],
                value_text=value_text,
                suffix_text=behavior[match.end():],
            )
    return ModuleCardUniqueText(prefix_text=f'{behavior} ', value_text=value_text, suffix_text='')


def _scaled_main_value(slot_type: str, module: ModuleSnapshot, *, role: str, slot_state: ModuleSystemState | None) -> tuple[float | None, str]:
    display = str(module.stat or '').strip()
    if role != 'assist':
        try:
            return float(display), _format_main_value_text(float(display), display)
        except ValueError:
            return None, _format_main_value_text(None, display)
    assist_level = slot_state.assist_level if slot_state else None
    lookup_eff = load_assist_efficiency_lookup().get(int(assist_level or -1))
    assist_multiplier_eff = (slot_state.multiplier_cap if slot_state and slot_state.multiplier_cap is not None else lookup_eff) if slot_state else lookup_eff
    try:
        base_value = float(display)
    except ValueError:
        base_value = None
    if assist_level is None or assist_multiplier_eff is None:
        return base_value, _format_main_value_text(base_value, display)
    full_assist_main = module_main_effect_multiplier(slot_type, module.rarity, int(assist_level))
    if full_assist_main is not None:
        scaled = 1.0 + (full_assist_main - 1.0) * assist_multiplier_eff
        return scaled, _format_main_value_text(scaled, None)
    if base_value is not None:
        scaled = 1.0 + (base_value - 1.0) * assist_multiplier_eff
        return scaled, _format_main_value_text(scaled, None)
    return None, _format_main_value_text(None, display)


def _scaled_unique_value(module_name: str, module: ModuleSnapshot, *, role: str, slot_state: ModuleSystemState | None) -> tuple[str | None, str | None]:
    rarity = str(module.rarity or '')
    assist_level = slot_state.assist_level if slot_state else None
    lookup_eff = load_assist_efficiency_lookup().get(int(assist_level or -1))
    assist_multiplier_eff = (slot_state.multiplier_cap if slot_state and slot_state.multiplier_cap is not None else lookup_eff) if slot_state else lookup_eff
    unique_rarity = normalize_module_unique_rarity(rarity)
    if role == 'assist' and slot_state and slot_state.rarity_cap:
        unique_rarity = normalize_module_unique_rarity(str(slot_state.rarity_cap))
    unique_lookup = load_module_unique_effect_values().get((_slug_text(module_name), unique_rarity))
    if unique_lookup is None:
        return None, None
    unique_value, unique_measure = unique_lookup
    if role == 'assist' and unique_value is not None and assist_multiplier_eff is not None:
        if unique_measure == 'count':
            unique_value = float(int(unique_value))
        else:
            unique_value = unique_value * assist_multiplier_eff
    return _format_unique_value_text(unique_value, unique_measure), unique_measure


def _scaled_substat_value(sub: ModuleSubstat, *, role: str, slot_state: ModuleSystemState | None) -> str:
    display = str(sub.value or '').strip()
    if role != 'assist':
        return display
    assist_level = slot_state.assist_level if slot_state else None
    lookup_eff = load_assist_efficiency_lookup().get(int(assist_level or -1))
    assist_substat_eff = (slot_state.substat_cap if slot_state and slot_state.substat_cap is not None else lookup_eff) if slot_state else lookup_eff
    if assist_substat_eff is None:
        return display
    value, suffix = _parse_token_value(display, sub.raw_token)
    if value is None:
        return display
    return _format_token_value(value * assist_substat_eff, suffix)


def _effect_slots_for_module(module: ModuleSnapshot, *, role: str, slot_state: ModuleSystemState | None, displayed_level: int | None) -> tuple[ModuleCardEffectSlot, ...]:
    unlock_levels = module_substat_unlock_levels()
    substats = list(module.substats or [])
    slots: list[ModuleCardEffectSlot] = []
    for idx, unlock_level in enumerate(unlock_levels, start=1):
        is_unlocked = displayed_level is not None and displayed_level >= unlock_level
        sub = substats[idx - 1] if idx - 1 < len(substats) else None
        if not is_unlocked:
            slots.append(ModuleCardEffectSlot(idx, 'locked', unlock_level, None, None, 'Locked', f'Unlocks at Lv. {unlock_level}'))
            continue
        if sub is None or (not str(sub.name or '').strip() and not str(sub.value or '').strip()):
            slots.append(ModuleCardEffectSlot(idx, 'empty', unlock_level, None, None, None, 'Empty substat slot'))
            continue
        rarity_text = _infer_substat_rarity(module.slot_type, sub, role=role, slot_state=slot_state)
        rarity_key = _MODULE_RARITY_KEY_MAP.get(rarity_text) if rarity_text else None
        slots.append(ModuleCardEffectSlot(
            slot_index=idx,
            state='populated',
            unlock_level=unlock_level,
            rarity_key=rarity_key,
            rarity_text=rarity_text,
            value_text=_scaled_substat_value(sub, role=role, slot_state=slot_state),
            label_text=_normalize_module_substat_name(sub.name),
        ))
    return tuple(slots)


def _payload_for_module(slot_type: str, module_name: str, module: ModuleSnapshot, *, role: str, slot_state: ModuleSystemState | None) -> ModuleCardPayload:
    rarity_text = str(module.rarity or '').strip()
    base_rarity, stars = normalize_module_base_rarity(rarity_text)
    rarity_key = _MODULE_RARITY_KEY_MAP.get(base_rarity or '')
    displayed_level = module.level if role == 'primary' else (slot_state.assist_level if slot_state else None)
    displayed_level_cap = module_level_cap(rarity_text) if role == 'primary' else None
    _, main_value_text = _scaled_main_value(slot_type, module, role=role, slot_state=slot_state)
    unique_value_text, unique_measure = _scaled_unique_value(module_name, module, role=role, slot_state=slot_state)
    role_bar_detail = '' if role == 'primary' else _format_assist_summary(slot_state)
    return ModuleCardPayload(
        module_name=module_name,
        slot_type=slot_type,
        role=role,
        rarity_text=rarity_text,
        rarity_key=rarity_key,
        stars=stars,
        displayed_level=displayed_level,
        displayed_level_cap=displayed_level_cap,
        level_text=_format_level_text(role=role, displayed_level=displayed_level, displayed_level_cap=displayed_level_cap),
        role_bar_label_text=role.title(),
        role_bar_detail_text=role_bar_detail,
        main_value_text=main_value_text,
        main_label_text=_MODULE_MAIN_LABELS.get(slot_type, slot_type.title()),
        unique_value_text=unique_value_text,
        unique_measure=unique_measure,
        unique_text=_build_unique_text(module_name, unique_value_text, unique_measure),
        effect_slots=_effect_slots_for_module(module, role=role, slot_state=slot_state, displayed_level=displayed_level),
    )


def build_module_card_payloads(account_state: AccountState) -> dict[str, Any]:
    presets: dict[str, dict[str, dict[str, Any]]] = {}
    for preset_name, slot_map in (account_state.module_presets or {}).items():
        preset_payload: dict[str, dict[str, Any]] = {}
        for slot_type in ('cannon', 'armor', 'generator', 'core'):
            selection = (slot_map or {}).get(slot_type)
            slot_state = (account_state.module_system_state or {}).get(slot_type)
            role_payload: dict[str, Any] = {}
            for role in ('primary', 'assist'):
                module_name = getattr(selection, role, None) if selection is not None else None
                if not module_name:
                    role_payload[role] = None
                    continue
                module = (account_state.modules_inventory or {}).get(module_name)
                if module is None:
                    role_payload[role] = None
                    continue
                role_payload[role] = asdict(_payload_for_module(slot_type, module_name, module, role=role, slot_state=slot_state))
            preset_payload[slot_type] = role_payload
        presets[preset_name] = preset_payload
    return {
        'artifact': 'module_card_payloads.json',
        'schema_version': 1,
        'presets': presets,
    }


def module_card_payload_contract_snapshot() -> dict[str, Any]:
    return {
        'artifact': 'module_card_payloads.json',
        'schema_version': 1,
        'owner': 'qe.query_module_policy',
        'slot_types': ['cannon', 'armor', 'generator', 'core'],
        'roles': ['primary', 'assist'],
        'effect_slot_count': 8,
    }
