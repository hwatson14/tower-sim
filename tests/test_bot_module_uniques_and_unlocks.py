from pathlib import Path
import yaml
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from input.ids_parser import parse_ids
from input.runtime_state import compile_account_state
from compilers.stat_input_compiler import compile_stat_inputs
from engine.stat_engine import resolve_stats

def _book(state_mode="start_of_run"):
    ids = parse_ids(ROOT / "input" / "imports" / "ids.csv")
    manual = yaml.safe_load((ROOT / "input" / "manual_inputs.yaml").read_text()) or {}
    loadout = manual.get("loadout") or {}
    perks = manual.get("perk_config") or {}
    acct = compile_account_state(ids, loadout_config=loadout, perk_config=perks)
    rows = compile_stat_inputs(acct, preset_name="Farming", state_mode=state_mode)
    return resolve_stats(rows)

def test_singularity_harness_unique_feeds_bot_global_range_bonus():
    book = _book()
    row = book.rows['mechanic_param::bot.global.range_bonus_m']
    assert row.status == 'resolved'
    assert abs(float(row.final_value) - 24.0) < 1e-9

def test_bot_unlock_flags_resolve_for_farming_account():
    book = _book()
    for key in ['capability::bot.golden.owned', 'capability::bot.amplify.owned', 'capability::bot.flame.owned', 'capability::bot.thunder.owned']:
        assert book.rows[key].status == 'resolved'
        assert bool(book.rows[key].final_value) is True
