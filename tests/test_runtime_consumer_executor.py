from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from engine.runtime_consumer_executor import RuntimeConsumerExecutor
from engine.stat_engine import resolve_stats
from parsers.ids_parser import parse_ids

ROOT = Path(__file__).resolve().parents[1]


def _build_statbook():
    ids_raw = parse_ids(ROOT / "input" / "_IDS.csv")
    state = compile_account_state(ids_raw, default_preset="Farming")
    stat_inputs = compile_stat_inputs(state, preset_name="Farming", state_mode="start_of_run")
    return resolve_stats(stat_inputs)


def test_runtime_consumer_executor_emits_skip_wave_outputs():
    statbook = _build_statbook()
    outputs = RuntimeConsumerExecutor().execute_skip_wave_outputs(statbook=statbook, target_display_wave=120)
    assert outputs.target_display_wave == 120
    assert outputs.attack_wave is not None and outputs.attack_wave >= 0
    assert outputs.health_wave is not None and outputs.health_wave >= 0
    assert outputs.attack_wave <= 120
    assert outputs.health_wave <= 120
