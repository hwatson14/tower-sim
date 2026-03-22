from pathlib import Path
import sys
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from compilers.stat_input_compiler import compile_stat_inputs
from engine.stat_engine import resolve_stats
from tests.helpers import build_state


@lru_cache(maxsize=None)
def _book(state_mode: str = 'start_of_run'):
    acct = build_state()
    rows = compile_stat_inputs(acct, preset_name='Farming', state_mode=state_mode)
    return resolve_stats(rows)


def test_bot_canonicals_resolve_through_stat_engine_start_of_run():
    book = _book('start_of_run')
    expected = {
        'mechanic_param::bot.golden.duration_seconds': 32.0,
        'mechanic_param::bot.golden.cooldown_seconds': 90.0,
        'mechanic_param::bot.golden.range_m': 74.0,
        'mechanic_param::bot.flame.cooldown_seconds': 26.0,
        'mechanic_param::bot.flame.range_m': 70.0,
        'mechanic_param::bot.amplify.range_m': 49.0,
        'mechanic_param::bot.thunder.linger_slow_pct': 0.2,
        'mechanic_param::bot.global.range_bonus_m': 24.0,
    }
    for key, value in expected.items():
        row = book.rows[key]
        assert row.status == 'resolved'
        assert abs(float(row.final_value) - value) < 1e-9


def test_bot_canonical_names_are_distinct_from_raw_runtime_inputs():
    book = _book('start_of_run')
    assert 'mechanic_param::bot.golden.duration_seconds' in book.rows
    assert 'mechanic_param::bot.golden.cooldown_seconds' in book.rows
    assert 'runtime_mechanic_param::bot.golden_bot.duration_seconds' not in book.rows
    assert 'runtime_mechanic_param::bot.golden_bot.cooldown_seconds' not in book.rows
