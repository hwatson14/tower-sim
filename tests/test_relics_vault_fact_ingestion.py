from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from input.runtime_state import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from input.ids_parser import parse_ids


def _build_state():
    return compile_account_state(parse_ids(ROOT / 'input' / 'imports' / 'ids.csv'), default_preset='Farming')


def test_relics_and_vault_compilation_keeps_only_fact_rows():
    state = _build_state()

    assert 'Misc.' not in state.relics
    assert 'Damage? ' not in state.relics
    assert 'Defense' not in state.relics
    assert 'Relics' not in state.relics
    assert 'Total Bonuses' not in state.relics

    assert 'Misc.' not in state.vault
    assert 'Attack' not in state.vault
    assert 'Defense' not in state.vault
    assert 'Utility' not in state.vault
    assert 'Total Bonuses' not in state.vault

    assert state.relics['Lab Speed'] == 0.395
    assert state.vault['Keys spent'] == 0
    assert state.vault['Ad Gems Stack'] == 1


def test_fact_only_compilation_removes_downstream_relic_vault_header_rows():
    state = _build_state()
    rows = compile_stat_inputs(state, preset_name='Farming', state_mode='start_of_run')
    by_family = {(row.source_family, row.source_name) for row in rows}

    for banned in [
        ('relic', 'Misc.'),
        ('relic', 'Damage? '),
        ('relic', 'Defense'),
        ('vault', 'Misc.'),
        ('vault', 'Attack'),
        ('vault', 'Defense'),
        ('vault', 'Utility'),
        ('vault', 'Total Bonuses'),
    ]:
        assert banned not in by_family
