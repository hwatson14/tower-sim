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


def test_v28_module_snapshot_publishes_selected_substat_rows() -> None:
    state = _base_account_state()
    rows = compile_stat_inputs(
        state,
        preset_name=state.default_preset,
        state_mode='start_of_run',
    )

    module_rows = [
        row for row in rows
        if row.source_family == 'module_substat'
    ]
    assert len(module_rows) == 39
    assert any(row.source_name == 'Amplifying Strike' and row.stat_name == 'Critical Factor' for row in module_rows)
    assert any(row.source_name == 'Primordial Collapse' and row.stat_name == 'Death Wave - Quantity' for row in module_rows)
    assert any(row.source_name == 'Om Chip' and row.stat_name == 'Spotlight - Bonus' for row in module_rows)


def test_v28_selected_assist_modules_emit_scaled_assist_rows() -> None:
    state = _base_account_state()
    rows = compile_stat_inputs(
        state,
        preset_name=state.default_preset,
        state_mode='start_of_run',
    )

    assist_rows = [
        row for row in rows
        if row.source_family == 'module_substat'
        and row.source_name in {'Orbital Augment', 'Black Hole Digestor'}
    ]
    assert {(row.source_name, row.stat_name, row.destination_id) for row in assist_rows} >= {
        ('Orbital Augment', 'Wall Health', 'wall_hp'),
        ('Black Hole Digestor', 'Enemy Attack Level Skip', 'enemy_attack_level_skip_pct'),
        ('Black Hole Digestor', 'Coins / Kill Bonus', 'coins_per_kill_bonus'),
    }
