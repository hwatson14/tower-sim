from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
from engine.progression_recalc_bridge import materialize_progression_family_baseline
from engine.scenario_engine import ScenarioConfig
from engine.timing_engine import materialize_timing_family_baseline
from parsers.ids_parser import parse_ids


@lru_cache(maxsize=None)
def _parsed_ids():
    return parse_ids(ROOT / 'input' / '_IDS.csv')


@lru_cache(maxsize=None)
def _json_config(filename: str):
    return json.loads((ROOT / 'input' / filename).read_text())


@lru_cache(maxsize=None)
def _compiled_state(loadout_filename: str, perks_filename: str):
    return compile_account_state(
        _parsed_ids(),
        default_preset='Farming',
        loadout_config=_json_config(loadout_filename),
        perk_config=_json_config(perks_filename),
    )


def build_state(*, loadout_filename: str = 'loadout.json', perks_filename: str = 'perks.json'):
    return copy.deepcopy(_compiled_state(loadout_filename, perks_filename))


@lru_cache(maxsize=None)
def _timing_query_state(family_id: str):
    state = _compiled_state('loadout.json', 'perks.json')
    if family_id == 'timing_tournament_no_perks':
        return replace(
            state,
            default_preset='Tourney',
            active_card_preset='Tourney',
            active_module_preset='Tourney',
            active_perk_preset='Tourney',
        )
    return state


def timing_family_context(family_id: str) -> tuple[ScenarioConfig, bool, str]:
    if family_id == 'timing_tournament_no_perks':
        return ScenarioConfig(mode_id='tournament', league='champion', tournament_wave=150), False, 'Tourney'
    if family_id == 'timing_farm_with_perks':
        return ScenarioConfig(mode_id='farming', tier=14), True, 'Farming'
    if family_id == 'timing_scenario_probe':
        return ScenarioConfig(mode_id='scenario_probe', tier=14), False, 'Farming'
    raise ValueError(f'Unsupported timing family {family_id!r}.')


@lru_cache(maxsize=None)
def _family_baseline(family_id: str):
    if family_id.startswith('progression_'):
        return materialize_progression_family_baseline(
            account_state=_compiled_state('loadout.json', 'perks.json'),
            family_id=family_id,
            preset_name='Farming',
            perks_enabled=family_id.endswith('with_perks'),
        )

    if family_id.startswith('timing_'):
        scenario_config, perks_enabled, preset_name = timing_family_context(family_id)
        return materialize_timing_family_baseline(
            account_state=_timing_query_state(family_id),
            family_id=family_id,
            preset_name=preset_name,
            scenario_config=scenario_config,
            perks_enabled=perks_enabled,
        )

    raise ValueError(f'Unsupported family {family_id!r}.')


def build_family_baseline(family_id: str):
    return _family_baseline(family_id)


@lru_cache(maxsize=None)
def cached_run_stats_output(*args: str) -> Path:
    key = hashlib.sha256(repr(args).encode('utf-8')).hexdigest()[:16]
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
