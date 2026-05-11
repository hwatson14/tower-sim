from __future__ import annotations

from functools import lru_cache

from input.loader import load_inputs
from input.runtime_state import build_runtime_state
from qe.stat_input_compiler import compile_stat_inputs


@lru_cache(maxsize=1)
def _base_account_state():
    bundle = load_inputs()
    return build_runtime_state(
        bundle.ids_raw,
        default_preset='Farming',
        loadout_config=bundle.loadout_config,
        perk_config=bundle.perk_config,
    )


def test_v28_locked_module_snapshot_has_no_selected_substat_rows() -> None:
    state = _base_account_state()
    rows = compile_stat_inputs(
        state,
        preset_name=state.default_preset,
        state_mode='start_of_run',
    )

    assert not [
        row for row in rows
        if row.source_family == 'module_substat'
    ]


def test_v28_locked_assist_modules_do_not_emit_scaled_assist_rows() -> None:
    state = _base_account_state()
    rows = compile_stat_inputs(
        state,
        preset_name=state.default_preset,
        state_mode='start_of_run',
    )

    assert not [
        row for row in rows
        if row.source_family == 'module_substat'
        and row.source_name in {'Orbital Augment', 'Black Hole Digestor'}
    ]
