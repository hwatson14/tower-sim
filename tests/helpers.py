from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

from input.runtime_state import build_runtime_state as compile_account_state
from simulators.progression import materialize_progression_family_baseline
from simulators.scenario import ScenarioConfig
from simulators.timing import materialize_timing_family_baseline
from input.ids_parser import parse_ids


@lru_cache(maxsize=None)
def _parsed_ids():
    return parse_ids(ROOT / 'input' / 'imports' / 'ids.csv')


@lru_cache(maxsize=None)
def _manual_inputs():
    return yaml.safe_load((ROOT / 'input' / 'manual_inputs.yaml').read_text()) or {}


_DERIVED_FILES = frozenset({
    'perks_derived.json',
})


@lru_cache(maxsize=None)
def _derived_perk_config(filename: str) -> dict:
    """Load a named perk config from input/derived/ (for testing projected-max states)."""
    return json.loads((ROOT / 'input' / 'derived' / filename).read_text())


@lru_cache(maxsize=None)
def _compiled_state(perk_config_key: str):
    """Compile account state. perk_config_key is 'default' or a derived filename."""
    if perk_config_key == 'default':
        perk_cfg = _manual_inputs().get('perk_config') or {}
    else:
        perk_cfg = _derived_perk_config(perk_config_key)
    loadout_cfg = _manual_inputs().get('loadout') or {}
    return compile_account_state(
        _parsed_ids(),
        default_preset='Farming',
        loadout_config=loadout_cfg,
        perk_config=perk_cfg,
    )


def build_state(*, perks_filename: str = 'default'):
    """
    Build an AccountState for tests.

    perks_filename: 'default' uses manual_inputs.yaml perk_config (empty, no active preset).
    Pass a derived filename like 'perks_derived.json' to test with specific perk states.
    """
    return copy.deepcopy(_compiled_state(perks_filename))


_TIMING_FAMILY_CANONICAL_PARAMS: dict[str, dict] = {
    'timing_tournament_no_perks': {
        'preset_name': 'Tourney',
        'scenario_config': ScenarioConfig(mode_id='tournament', league='champion', tournament_wave=150),
        'perks_enabled': False,
    },
    'timing_farm_with_perks': {
        'preset_name': 'Farming',
        'scenario_config': ScenarioConfig(mode_id='farming', tier=14),
        'perks_enabled': True,
    },
    'timing_scenario_probe': {
        'preset_name': 'Farming',
        'scenario_config': ScenarioConfig(mode_id='scenario_probe', tier=14),
        'perks_enabled': False,
    },
}


def timing_family_context(family_id: str) -> tuple:
    """Return (ScenarioConfig, perks_enabled, preset_name) for a timing family."""
    params = _TIMING_FAMILY_CANONICAL_PARAMS[family_id]
    return params['scenario_config'], params['perks_enabled'], params['preset_name']

_PROGRESSION_FAMILY_CANONICAL_PARAMS: dict[str, dict] = {
    'progression_start_of_run': {
        'preset_name': 'Farming',
        'state_mode': 'start_of_run',
        'perks_enabled': False,
    },
    'progression_runtime_no_perks': {
        'preset_name': 'Farming',
        'state_mode': 'start_of_run',
        'perks_enabled': False,
    },
    'progression_runtime_with_perks': {
        'preset_name': 'Farming',
        'state_mode': 'start_of_run',
        'perks_enabled': True,
    },
}


def progression_family_context(family_id: str) -> dict:
    return dict(_PROGRESSION_FAMILY_CANONICAL_PARAMS[family_id])



@lru_cache(maxsize=None)
def build_family_baseline(family_id: str):
    """Return an immutable FamilyBaselineContributorMap for the given declared family_id using canonical test params."""
    if family_id in _TIMING_FAMILY_CANONICAL_PARAMS:
        params = _TIMING_FAMILY_CANONICAL_PARAMS[family_id]
        return materialize_timing_family_baseline(
            account_state=build_state(),
            family_id=family_id,
            **params,
        )
    if family_id in _PROGRESSION_FAMILY_CANONICAL_PARAMS:
        params = _PROGRESSION_FAMILY_CANONICAL_PARAMS[family_id]
        return materialize_progression_family_baseline(
            account_state=build_state(),
            family_id=family_id,
            **params,
        )
    raise NotImplementedError(f'No canonical test params registered for family_id={family_id!r}')


@lru_cache(maxsize=None)
def cached_run_stats_output(*args: str) -> Path:
    try:
        repo_rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        repo_rev = 'no-git-head'
    key = hashlib.sha256((repo_rev + '::' + repr(args)).encode('utf-8')).hexdigest()[:16]
    out = Path(tempfile.gettempdir()) / 'tower_sim_pytest_run_stats' / key
    diagnostics_path = out / 'diagnostics.json'
    if diagnostics_path.exists():
        return out
    out.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(ROOT / 'run_stats.py'), *args, '--out', str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or f'run_stats failed for args={args!r}')
    return out
