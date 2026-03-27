from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from input.runtime_state import ScenarioRuntimeInputs


def test_scenario_runtime_inputs_from_mapping_accepts_namespaced_keys():
    inputs = ScenarioRuntimeInputs.from_mapping({
        'runtime_mechanic_param::combat.orb_boss_hit_pct': 2.5,
        'runtime_mechanic_param::combat.effective_damage_reduction_pct': 98.0,
    })
    assert inputs.orb_boss_hit_pct == 2.5
    assert inputs.effective_damage_reduction_pct == 98.0


def test_scenario_runtime_inputs_validate_ranges():
    try:
        ScenarioRuntimeInputs.from_mapping({'effective_damage_reduction_pct': 120.0})
    except ValueError as exc:
        assert '<= 100.0' in str(exc)
    else:
        raise AssertionError('Expected range validation failure.')


def test_scenario_runtime_inputs_contract_declares_all_dataclass_fields():
    contract = yaml.safe_load((ROOT / 'kb' / 'global-rules' / 'contracts' / 'scenario-runtime-inputs.yaml').read_text())
    fields = set((contract or {}).get('fields', {}).keys())
    expected = {
        'orb_boss_hit_pct',
        'orb_boss_hits_per_second',
        'electron_hits_per_second',
        'boss_contact_time_seconds',
        'boss_hit_interval_seconds',
        'effective_damage_reduction_pct',
        'incoming_damage_multiplier',
        'boss_wave_interval',
        'enemy_level_skip_reduction_pp',
    }
    assert fields == expected


def test_scenario_runtime_inputs_contract_validates_positive_rate_fields():
    try:
        ScenarioRuntimeInputs.from_mapping({'electron_hits_per_second': 0.0})
    except ValueError as exc:
        assert '> 0.0' in str(exc)
    else:
        raise AssertionError('Expected positive-rate validation failure.')
