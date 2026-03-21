from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
import engine.incremental_subset_executor as incremental_subset_executor
from engine.incremental_subset_executor import IncrementalSubsetExecutor
from engine.scenario_engine import ScenarioConfig
from engine.stat_engine import resolve_stats
from engine.timing_engine import resolve_timing_family_query
from parsers.ids_parser import parse_ids

ROOT = Path(__file__).resolve().parents[1]


def _inputs():
    ids_raw = parse_ids(ROOT / 'input' / '_IDS.csv')
    state = compile_account_state(ids_raw, default_preset='Farming')
    return compile_stat_inputs(state, preset_name='Farming', state_mode='start_of_run', perks_enabled=True)


def test_subset_executor_matches_health_chain():
    stat_inputs = _inputs()
    candidate = IncrementalSubsetExecutor().execute(stat_inputs, ['canonical_stat::tower_hp', 'canonical_stat::wall_hp'])
    reference = resolve_stats(stat_inputs)
    assert candidate['canonical_stat::tower_hp'].final_value == reference.rows['canonical_stat::tower_hp'].final_value
    assert candidate['canonical_stat::wall_hp'].final_value == reference.rows['canonical_stat::wall_hp'].final_value


def test_subset_executor_matches_free_upgrade_support_path():
    stat_inputs = _inputs()
    candidate = IncrementalSubsetExecutor().execute(stat_inputs, ['canonical_stat::free_attack_upgrade_chance_pct'])
    reference = resolve_stats(stat_inputs)
    assert 'canonical_stat::free_upgrade_multiplier' in candidate
    assert candidate['canonical_stat::free_attack_upgrade_chance_pct'].final_value == reference.rows['canonical_stat::free_attack_upgrade_chance_pct'].final_value


def test_subset_executor_matches_defense_path():
    stat_inputs = _inputs()
    candidate = IncrementalSubsetExecutor().execute(stat_inputs, ['canonical_stat::tower_defense_pct'])
    reference = resolve_stats(stat_inputs)
    assert candidate['canonical_stat::tower_defense_pct'].final_value == reference.rows['canonical_stat::tower_defense_pct'].final_value


def test_subset_executor_matches_thorns_path():
    stat_inputs = _inputs()
    candidate = IncrementalSubsetExecutor().execute(stat_inputs, ['canonical_stat::tower_thorns_damage_pct'])
    reference = resolve_stats(stat_inputs)
    assert candidate['canonical_stat::tower_thorns_damage_pct'].final_value == reference.rows['canonical_stat::tower_thorns_damage_pct'].final_value


def test_subset_executor_matches_orb_speed_path():
    stat_inputs = _inputs()
    candidate = IncrementalSubsetExecutor().execute(stat_inputs, ['canonical_stat::tower_orb_speed_rpm'])
    reference = resolve_stats(stat_inputs)
    assert candidate['canonical_stat::tower_orb_speed_rpm'].final_value == reference.rows['canonical_stat::tower_orb_speed_rpm'].final_value


def test_subset_executor_matches_free_defense_upgrade_support_path():
    stat_inputs = _inputs()
    candidate = IncrementalSubsetExecutor().execute(stat_inputs, ['canonical_stat::free_defense_upgrade_chance_pct'])
    reference = resolve_stats(stat_inputs)
    assert 'canonical_stat::free_upgrade_multiplier' in candidate
    assert candidate['canonical_stat::free_defense_upgrade_chance_pct'].final_value == reference.rows['canonical_stat::free_defense_upgrade_chance_pct'].final_value


def test_subset_executor_matches_free_utility_upgrade_support_path():
    stat_inputs = _inputs()
    candidate = IncrementalSubsetExecutor().execute(stat_inputs, ['canonical_stat::free_utility_upgrade_chance_pct'])
    reference = resolve_stats(stat_inputs)
    assert 'canonical_stat::free_upgrade_multiplier' in candidate
    assert candidate['canonical_stat::free_utility_upgrade_chance_pct'].final_value == reference.rows['canonical_stat::free_utility_upgrade_chance_pct'].final_value


def test_subset_executor_matches_enemy_attack_level_skip_path():
    stat_inputs = _inputs()
    candidate = IncrementalSubsetExecutor().execute(stat_inputs, ['canonical_stat::enemy_attack_level_skip_pct'])
    reference = resolve_stats(stat_inputs)
    assert candidate['canonical_stat::enemy_attack_level_skip_pct'].final_value == reference.rows['canonical_stat::enemy_attack_level_skip_pct'].final_value


def test_subset_executor_matches_enemy_health_level_skip_path():
    stat_inputs = _inputs()
    candidate = IncrementalSubsetExecutor().execute(stat_inputs, ['canonical_stat::enemy_health_level_skip_pct'])
    reference = resolve_stats(stat_inputs)
    assert candidate['canonical_stat::enemy_health_level_skip_pct'].final_value == reference.rows['canonical_stat::enemy_health_level_skip_pct'].final_value




def test_subset_executor_module_does_not_import_stat_engine_directly():
    module_source = Path(incremental_subset_executor.__file__).read_text()
    assert 'from engine.stat_engine import' not in module_source
    assert 'import engine.stat_engine' not in module_source
    assert 'from engine.stat_resolution_core import' in module_source

def test_subset_executor_resolves_timing_wave_duration_natively_without_full_statbook(monkeypatch):
    ids_raw = parse_ids(ROOT / 'input' / '_IDS.csv')
    state = compile_account_state(ids_raw, default_preset='Farming')
    stat_inputs = compile_stat_inputs(state, preset_name='Farming', state_mode='start_of_run', perks_enabled=True)

    def _boom(_):
        raise AssertionError('resolve_stats should not be used by the bounded subset executor')

    monkeypatch.setattr(incremental_subset_executor, 'resolve_stats', _boom, raising=False)
    candidate = IncrementalSubsetExecutor().execute(
        stat_inputs,
        [
            'runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration',
            'support_surface::timing.wave_duration_seconds_effective',
        ],
        family_id='timing_farm_with_perks',
    )

    assert candidate['runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration'].final_value > 0
    assert candidate['support_surface::timing.wave_duration_seconds_effective'].final_value == pytest.approx(16.1)


def test_subset_executor_matches_timing_core_cycle_bundle_values():
    ids_raw = parse_ids(ROOT / 'input' / '_IDS.csv')
    state = compile_account_state(ids_raw, default_preset='Farming')
    stat_inputs = compile_stat_inputs(state, preset_name='Farming', state_mode='start_of_run', perks_enabled=True)
    candidate = IncrementalSubsetExecutor().execute(
        stat_inputs,
        [
            'mechanic_param::uw.black_hole.cooldown_seconds',
            'mechanic_param::uw.black_hole.duration_seconds',
            'mechanic_param::uw.golden_tower.cooldown_seconds',
            'mechanic_param::uw.golden_tower.duration_seconds',
        ],
        family_id='timing_farm_with_perks',
    )
    reference = resolve_stats(stat_inputs)
    for node in [
        'mechanic_param::uw.black_hole.cooldown_seconds',
        'mechanic_param::uw.black_hole.duration_seconds',
        'mechanic_param::uw.golden_tower.cooldown_seconds',
        'mechanic_param::uw.golden_tower.duration_seconds',
    ]:
        assert candidate[node].final_value == reference.rows[node].final_value


def test_subset_executor_matches_timing_wave_duration_bundle_from_timing_family_baseline():
    ids_raw = parse_ids(ROOT / 'input' / '_IDS.csv')
    state = compile_account_state(ids_raw, default_preset='Farming')
    candidate = IncrementalSubsetExecutor().execute(
        compile_stat_inputs(state, preset_name='Farming', state_mode='start_of_run', perks_enabled=True),
        [
            'runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration',
            'support_surface::timing.wave_duration_seconds_effective',
        ],
        family_id='timing_farm_with_perks',
    )
    reference = resolve_timing_family_query(
        account_state=state,
        family_id='timing_farm_with_perks',
        preset_name='Farming',
        scenario_config=ScenarioConfig(mode_id='farming', tier=14),
        perks_enabled=True,
        requested_surface_ids=(
            'runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration',
            'support_surface::timing.wave_duration_seconds_effective',
        ),
        trace_mode='contributors',
    )
    reference_rows = {row.surface_id: row for row in reference.resolved_surface_rows}
    assert candidate['runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration'].final_value == reference_rows['runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration'].final_value
    assert candidate['support_surface::timing.wave_duration_seconds_effective'].final_value == reference_rows['support_surface::timing.wave_duration_seconds_effective'].final_value
