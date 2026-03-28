from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from input.runtime_state import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from engine.incremental_parity_harness import IncrementalParityHarness
from engine.incremental_subset_executor import IncrementalSubsetExecutor
from engine.stat_engine import resolve_stats
from input.ids_parser import parse_ids

ROOT = Path(__file__).resolve().parents[1]


def test_parity_harness_passes_for_closed_subset():
    ids_raw = parse_ids(ROOT / 'input' / 'imports' / 'ids.csv')
    state = compile_account_state(ids_raw, default_preset='Farming')
    inputs = compile_stat_inputs(state, preset_name='Farming', state_mode='start_of_run', perks_enabled=True)
    candidate = IncrementalSubsetExecutor().execute(inputs, ['canonical_stat::tower_orb_count'])
    reference = resolve_stats(inputs)
    result = IncrementalParityHarness().compare(candidate, reference)
    assert result.status == 'pass'
    assert result.mismatches == {}
