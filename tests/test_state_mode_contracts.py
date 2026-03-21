from compilers.stat_input_compiler import (
    SUPPORTED_STATE_MODES,
    normalize_state_mode,
    state_mode_support,
)


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
