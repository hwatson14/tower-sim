"""
input/lab_category_registry.py — Authoritative lab taxonomy loader for UI grouping.

Owns: loading and validation of kb/labs/tables/lab-category-registry.csv keyed by
exact IDS raw lab names.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_LAB_CATEGORY_REGISTRY_PATH = ROOT / 'kb' / 'labs' / 'tables' / 'lab-category-registry.csv'

_ALLOWED_CATEGORY_WIKI = {
    'main_research',
    'attack_research',
    'defense_research',
    'utility_research',
    'ultimate_weapon_research',
    'card_research',
    'perk_research',
    'bot_research',
    'enemies_research',
    'module_research',
    'battle_condition_research',
}

_ALLOWED_CATEGORY_UI = {
    'main',
    'attack',
    'defense',
    'utility',
    'ultimate_weapons',
    'cards',
    'perks',
    'bots',
    'enemies',
    'modules',
    'battle_conditions',
}


@lru_cache(maxsize=1)
def load_lab_category_registry_rows() -> list[dict[str, str]]:
    if not _LAB_CATEGORY_REGISTRY_PATH.exists():
        raise ValueError(f'Lab category registry missing: {_LAB_CATEGORY_REGISTRY_PATH}')

    with _LAB_CATEGORY_REGISTRY_PATH.open('r', encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))

    required_columns = {
        'raw_lab_name',
        'category_wiki',
        'category_ui',
        'category_detail',
        'source_basis',
        'mapping_confidence',
        'notes',
    }
    if not rows:
        raise ValueError('Lab category registry is empty.')
    if set(rows[0].keys()) != required_columns:
        raise ValueError('Lab category registry columns do not match required schema.')

    seen: set[str] = set()
    normalized_rows: list[dict[str, str]] = []
    for idx, row in enumerate(rows, start=2):
        normalized = {key: str(value or '').strip() for key, value in row.items()}
        raw_lab_name = normalized['raw_lab_name']
        if not raw_lab_name:
            raise ValueError(f'Lab category registry row {idx} has empty raw_lab_name.')
        if raw_lab_name == 'END OF ARRAY':
            raise ValueError('Lab category registry must not contain END OF ARRAY sentinel.')
        if raw_lab_name in seen:
            raise ValueError(f'Duplicate raw_lab_name in lab category registry: {raw_lab_name!r}')
        seen.add(raw_lab_name)

        if normalized['category_wiki'] not in _ALLOWED_CATEGORY_WIKI:
            raise ValueError(
                f'Invalid category_wiki for {raw_lab_name!r}: {normalized["category_wiki"]!r}'
            )
        if normalized['category_ui'] not in _ALLOWED_CATEGORY_UI:
            raise ValueError(
                f'Invalid category_ui for {raw_lab_name!r}: {normalized["category_ui"]!r}'
            )

        normalized_rows.append(normalized)

    return normalized_rows


@lru_cache(maxsize=1)
def load_lab_category_registry_by_raw_name() -> dict[str, dict[str, str]]:
    rows = load_lab_category_registry_rows()
    return {row['raw_lab_name']: row for row in rows}

