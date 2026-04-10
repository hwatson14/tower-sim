from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from qe.contracts import load_yaml_contract
from qe.models import StatInput

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / 'kb'
KB_CONTRACTS = KB / 'global-rules' / 'contracts'
STATE_MODE_CONTRACTS_PATH = KB_CONTRACTS / 'state-modes.yaml'


@lru_cache(maxsize=1)
def load_state_mode_contracts() -> dict:
    raw = load_yaml_contract(str(STATE_MODE_CONTRACTS_PATH))
    aliases = raw.get('state_mode_aliases') or {}
    modes = raw.get('state_modes') or {}
    normalized_modes = {}
    for mode_name, spec in modes.items():
        spec = spec or {}
        normalized_modes[mode_name] = {
            'excluded_source_families': set(spec.get('excluded_source_families') or []),
            'projection_facets_applied': list(spec.get('projection_facets_applied') or []),
            'notes': list(spec.get('notes') or []),
        }
    return {
        'aliases': aliases,
        'modes': normalized_modes,
    }


def supported_state_modes() -> tuple[str, ...]:
    return tuple(load_state_mode_contracts()['modes'].keys())


SUPPORTED_STATE_MODES = supported_state_modes()


def normalize_state_mode(state_mode: str | None) -> str:
    contracts = load_state_mode_contracts()
    mode = (state_mode or 'start_of_run').strip()
    mode = contracts['aliases'].get(mode, mode)
    if mode not in contracts['modes']:
        raise ValueError(f'Unsupported state_mode: {state_mode}')
    return mode


def state_mode_support(state_mode: str | None) -> dict:
    mode = normalize_state_mode(state_mode)
    spec = load_state_mode_contracts()['modes'][mode]
    return {
        'state_mode': mode,
        'supported': True,
        'projection_facets_applied': list(spec['projection_facets_applied']),
        'projection_facets_missing': [],
        'notes': list(spec['notes']),
    }


def row_in_state_mode(row: StatInput, state_mode: str | None) -> bool:
    mode = normalize_state_mode(state_mode)
    excluded = load_state_mode_contracts()['modes'][mode]['excluded_source_families']
    return row.source_family not in excluded
