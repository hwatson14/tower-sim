from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from compilers.account_state_compiler import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from models.bound_preset_family import bind_preset_family
from parsers.ids_parser import parse_ids


def test_bound_preset_family_rejects_independent_loadout_lane_binding():
    with pytest.raises(ValueError):
        bind_preset_family(
            preset_name='Farming',
            state_mode='start_of_run',
            perk_namespace_class='canonical',
            explicit_card_preset_name='Tourney',
            explicit_module_preset_name=None,
            explicit_perk_preset_name=None,
            active_perk_preset_name='Farming',
            perks_enabled=None,
        )


def test_bound_preset_family_rejects_canonical_perk_mismatch():
    with pytest.raises(ValueError):
        bind_preset_family(
            preset_name='Farming',
            state_mode='start_of_run',
            perk_namespace_class='canonical',
            explicit_card_preset_name=None,
            explicit_module_preset_name=None,
            explicit_perk_preset_name='Milestone',
            active_perk_preset_name='Milestone',
            perks_enabled=None,
        )


def test_bound_preset_family_allows_transient_perk_mismatch():
    bound = bind_preset_family(
        preset_name='Farming',
        state_mode='max_progression',
        perk_namespace_class='transient',
        explicit_card_preset_name=None,
        explicit_module_preset_name=None,
        explicit_perk_preset_name='ProjectedMax_AllAllowedExceptBanned',
        active_perk_preset_name='ProjectedMax_AllAllowedExceptBanned',
        perks_enabled=True,
    )
    assert bound.perk_preset_name == 'ProjectedMax_AllAllowedExceptBanned'
    assert bound.perks_enabled is True


def test_compile_stat_inputs_uses_bound_preset_lanes_not_active_lane_fallbacks():
    ids = parse_ids(ROOT / 'input' / 'imports' / 'ids.csv')
    state = compile_account_state(ids)
    mutated = replace(state, active_card_preset='Tourney', active_module_preset='Tourney')
    rows = compile_stat_inputs(mutated, preset_name='Farming', state_mode='start_of_run')
    card_rows = [row for row in rows if row.source_family == 'card']
    module_rows = [row for row in rows if row.source_family in {'module', 'module_substat'}]
    assert card_rows, "Expected card rows for bound preset lane validation."
    assert module_rows, "Expected module rows for bound preset lane validation."
    assert all(row.preset_name == 'Farming' for row in card_rows)
    assert all(row.preset_name == 'Farming' for row in module_rows)
