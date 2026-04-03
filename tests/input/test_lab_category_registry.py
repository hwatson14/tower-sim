from __future__ import annotations

import csv
from pathlib import Path

from input.ids_parser import parse_ids
from input.lab_category_registry import load_lab_category_registry_by_raw_name

ROOT = Path(__file__).resolve().parents[2]
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


def test_lab_category_registry_ids_coverage_duplicates_and_enums() -> None:
    ids = parse_ids(ROOT / 'input' / 'imports' / 'ids.csv')
    ids_names = {
        str((row or [''])[0]).strip()
        for row in (ids.raw_sections.get('Labs') or [])
        if str((row or [''])[0]).strip() and str((row or [''])[0]).strip() != 'END OF ARRAY'
    }

    registry_path = ROOT / 'kb' / 'labs' / 'tables' / 'lab-category-registry.csv'
    with registry_path.open('r', encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))

    seen: set[str] = set()
    for row in rows:
        raw_lab_name = str(row.get('raw_lab_name') or '').strip()
        assert raw_lab_name
        assert raw_lab_name != 'END OF ARRAY'
        assert raw_lab_name not in seen
        seen.add(raw_lab_name)
        assert str(row.get('category_wiki') or '').strip() in _ALLOWED_CATEGORY_WIKI
        assert str(row.get('category_ui') or '').strip() in _ALLOWED_CATEGORY_UI

    assert ids_names == seen


def test_lab_category_registry_does_not_use_misc_category() -> None:
    mapping = load_lab_category_registry_by_raw_name()
    assert mapping
    assert all(str(row.get('category_ui') or '').strip() != 'misc' for row in mapping.values())

