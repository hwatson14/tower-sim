from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import _normalize_preset_name
from models.account_state import PRESET_NAMES
from models.preset_contract import CANONICAL_PRESET_NAMES, load_preset_contract, load_section_layout_contract


def test_canonical_presets_are_loaded_from_registry_contract():
    contract = load_preset_contract()
    assert contract['canonical_presets'] == CANONICAL_PRESET_NAMES
    assert list(CANONICAL_PRESET_NAMES) == PRESET_NAMES
    assert CANONICAL_PRESET_NAMES == ('Tourney', 'Farming', 'Milestone', 'Preset 4', 'Preset 5')


def test_ingestion_aliases_normalize_only_to_canonical_presets():
    assert _normalize_preset_name('Testing') == 'Milestone'
    assert _normalize_preset_name('Preset 3') == 'Milestone'
    assert _normalize_preset_name('Placeholder 4th preset') == 'Preset 4'
    assert _normalize_preset_name('Placeholder 5th preset') == 'Preset 5'
    assert _normalize_preset_name('Not A Preset') is None


def test_section_layout_contract_owns_active_preset_column_truth():
    contract = load_section_layout_contract()
    assert contract['workshop']['preset_level_columns'] == {
        'Farming': 1,
        'Tourney': 3,
        'Milestone': 5,
        'Preset 4': 7,
        'Preset 5': 9,
    }
    assert contract['cards']['preset_assignment_columns']['Preset 4'] == 6
    assert contract['modules']['preset_label_aliases']['Placeholder 5th preset'] == 'Preset 5'


def test_registry_yaml_files_exist_with_expected_shapes():
    preset_contract = yaml.safe_load((ROOT / 'registry' / 'preset_contract.yaml').read_text())
    section_layout_contract = yaml.safe_load((ROOT / 'registry' / 'section_layout_contract.yaml').read_text())

    assert 'canonical_presets' in preset_contract
    assert 'aliases' in preset_contract
    assert 'sections' in section_layout_contract
    assert {'workshop', 'cards', 'modules'} <= set(section_layout_contract['sections'])
