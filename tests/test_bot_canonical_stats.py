from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from parsers.ids_parser import parse_ids
from compilers.account_state_compiler import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from engine.stat_engine import resolve_stats


def _book(state_mode: str = 'start_of_run'):
    ids = parse_ids(ROOT / 'input' / 'imports' / 'ids.csv')
    loadout = json.load(open(ROOT / 'input' / 'loadout.json'))
    perks = json.load(open(ROOT / 'input' / 'perks.json'))
    acct = compile_account_state(ids, loadout_config=loadout, perk_config=perks)
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
