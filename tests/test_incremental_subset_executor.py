from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from engine.incremental_subset_executor import IncrementalSubsetExecutor
from engine.stat_engine import resolve_stats
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
