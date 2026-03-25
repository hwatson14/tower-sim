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

from compilers.account_state_compiler import compile_account_state
from engine.progression_recalc_bridge import materialize_progression_family_baseline
from engine.scenario_engine import ScenarioConfig
from engine.timing_engine import materialize_timing_family_baseline
from parsers.ids_parser import parse_ids


@lru_cache(maxsize=None)
def _parsed_ids():
    return parse_ids(ROOT / 'input' / 'imports' / 'ids.csv')


_GENERATED_FILES = frozenset({
    'perks_projected_max.json',
    'perks_projected_max.timeline.json',
    'perks_projected_max.final_state.json',
    'perks_projected_max.diagnostics.json',
    'perks_max_progression_policy.runtime.json',
})

@lru_cache(maxsize=None)
def _json_config(filename: str):
    if filename in _GENERATED_FILES:
        return json.loads((ROOT / 'input' / 'derived' / filename).read_text())
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


def build_family_baseline(family_id: str):
    """Materialize a family baseline using the golden account state and canonical defaults per family."""
    state = build_state()
    if family_id == 'timing_tournament_no_perks':
        return materialize_timing_family_baseline(
            account_state=state,
            family_id=family_id,
            preset_name='Tourney',
            scenario_config=ScenarioConfig(mode_id='tournament', league='champion', tournament_wave=150),
            perks_enabled=False,
        )
    if family_id == 'timing_farm_with_perks':
        return materialize_timing_family_baseline(
            account_state=state,
            family_id=family_id,
            preset_name='Farming',
            scenario_config=ScenarioConfig(mode_id='farming', tier=14),
            perks_enabled=True,
        )
    if family_id == 'timing_scenario_probe':
        return materialize_timing_family_baseline(
            account_state=state,
            family_id=family_id,
            preset_name='Farming',
            scenario_config=ScenarioConfig(mode_id='scenario_probe', tier=14),
            perks_enabled=False,
        )
    if family_id in ('progression_start_of_run', 'progression_runtime_no_perks', 'progression_runtime_with_perks'):
        return materialize_progression_family_baseline(
            account_state=state,
            family_id=family_id,
        )
    raise ValueError(f'build_family_baseline: unknown family_id {family_id!r}')


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
