from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compilers.account_state_compiler import compile_account_state
from parsers.ids_parser import parse_ids


@dataclass(frozen=True)
class RunStatsResult:
    returncode: int
    stdout: str
    stderr: str


@lru_cache(maxsize=None)
def _build_state_cached(
    *,
    perks_filename: str = 'perks.json',
    loadout_filename: str = 'loadout.json',
    default_preset: str = 'Farming',
):
    ids = parse_ids(ROOT / 'input' / '_IDS.csv')
    loadout = json.loads((ROOT / 'input' / loadout_filename).read_text())
    perks = json.loads((ROOT / 'input' / perks_filename).read_text())
    return compile_account_state(ids, default_preset=default_preset, loadout_config=loadout, perk_config=perks)


def build_state(
    *,
    perks_filename: str = 'perks.json',
    loadout_filename: str = 'loadout.json',
    default_preset: str = 'Farming',
):
    return copy.deepcopy(
        _build_state_cached(
            perks_filename=perks_filename,
            loadout_filename=loadout_filename,
            default_preset=default_preset,
        )
    )


@contextlib.contextmanager
def _pushd(path: str | os.PathLike[str] | None):
    if path is None:
        yield
        return
    original = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original)


def run_stats_subprocess(argv, *, cwd=None, capture_output=False, text=False, check=False):
    import run_stats

    args = list(argv)
    if len(args) >= 2 and str(args[1]).endswith('run_stats.py'):
        args = args[2:]
    elif args and str(args[0]).endswith('run_stats.py'):
        args = args[1:]

    old_argv = sys.argv[:]
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    try:
        sys.argv = ['run_stats.py', *[str(arg) for arg in args]]
        with _pushd(cwd), contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            returncode = int(run_stats.main())
    finally:
        sys.argv = old_argv

    result = RunStatsResult(
        returncode=returncode,
        stdout=stdout_buffer.getvalue(),
        stderr=stderr_buffer.getvalue(),
    )
    if check and returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or f'run_stats.py exited with {returncode}')
    if capture_output or text:
        return result
    return result
