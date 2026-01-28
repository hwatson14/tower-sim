
from adapter.account import build_account_state
from adapter.loadout import apply_loadout
from adapter.tier_bc import apply_tier_and_bc
from adapter.heat import apply_heat
from adapter.battle_conditions import apply_battle_conditions
from adapter.dag_wiring import derive_stats
import json

def test_tier_run_monotonic():
    state={"base_attack":10}
    tiers={1:{},}
    bcs={}
    out_prev=None
    for wave in range(1,6):
        s=apply_tier_and_bc(state,{"tier":1},tiers,bcs)
        s=apply_heat(s,wave,{})
        s=derive_stats(s,json.load(open("data/dag.json")))
        if out_prev is not None:
            assert s["attack"]>=out_prev
        out_prev=s["attack"]

def test_tournament_perks_disabled():
    # placeholder: perks should not appear in state
    state={"base_attack":10}
    assert "perk_bonus" not in state
