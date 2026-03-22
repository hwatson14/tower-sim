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
