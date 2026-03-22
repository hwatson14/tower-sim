from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.stat_input_compiler import (
    SUPPORTED_STATE_MODES,
    normalize_state_mode,
    state_mode_support,
)
from engine import query_state_mode_policy


def test_supported_state_modes_from_contract():
    assert SUPPORTED_STATE_MODES == (
        'account_baseline',
        'gem_respec',
        'start_of_run',
        'max_progression',
    )


def test_state_mode_alias_and_notes_from_contract():
    assert normalize_state_mode('with_loadout') == 'start_of_run'
    support = state_mode_support('max_progression')
    assert support['projection_facets_applied'] == ['max_workshop']
    assert any('Perks can be materialized' in note for note in support['notes'])


def test_compiler_state_mode_api_delegates_to_query_owner():
    assert SUPPORTED_STATE_MODES is query_state_mode_policy.SUPPORTED_STATE_MODES
    assert normalize_state_mode is query_state_mode_policy.normalize_state_mode
    assert state_mode_support is query_state_mode_policy.state_mode_support
