from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from engine.incremental_overlay_publisher import IncrementalOverlayPublisher
from engine.incremental_subset_executor import IncrementalSubsetExecutor
from engine.stat_engine import resolve_stats
from parsers.ids_parser import parse_ids

ROOT = Path(__file__).resolve().parents[1]


def test_overlay_publisher_returns_complete_statbook():
    ids_raw = parse_ids(ROOT / 'input' / 'imports' / 'ids.csv')
    state = compile_account_state(ids_raw, default_preset='Farming')
    inputs = compile_stat_inputs(state, preset_name='Farming', state_mode='start_of_run', perks_enabled=True)
    reference = resolve_stats(inputs)
    candidate = IncrementalSubsetExecutor().execute(inputs, ['canonical_stat::tower_orb_count'])
    published = IncrementalOverlayPublisher().publish(reference, candidate)
    assert 'canonical_stat::tower_orb_count' in published.rows
    assert 'canonical_stat::tower_hp' in published.rows
    assert published.diagnostics['incremental_overlay']['status'] == 'published_candidate_overlay_over_full_reference'


def test_overlay_publisher_structurally_shares_unchanged_rows_and_does_not_mutate_reference_diagnostics():
    ids_raw = parse_ids(ROOT / 'input' / 'imports' / 'ids.csv')
    state = compile_account_state(ids_raw, default_preset='Farming')
    inputs = compile_stat_inputs(state, preset_name='Farming', state_mode='start_of_run', perks_enabled=True)
    reference = resolve_stats(inputs)
    original_diag = dict(reference.diagnostics)
    unchanged_before = reference.rows['canonical_stat::tower_hp']
    candidate = IncrementalSubsetExecutor().execute(inputs, ['canonical_stat::tower_orb_count'])
    published = IncrementalOverlayPublisher().publish(reference, candidate)
    assert published.rows['canonical_stat::tower_hp'] is unchanged_before
    assert reference.diagnostics == original_diag
    assert 'incremental_overlay' not in reference.diagnostics
    assert published.diagnostics['incremental_overlay']['sharing_mode'] == 'structural_share_unchanged_rows'
