from __future__ import annotations

import json
from pathlib import Path

from helpers import cached_run_stats_output


def test_run_stats_runtime_validation_emits_phase3_surfaces_and_optimizer_scores():
    out_dir = cached_run_stats_output()
    statbook = json.loads((out_dir / "statbook.json").read_text(encoding="utf-8"))
    optimizer = json.loads((out_dir / "optimizer_scores.json").read_text(encoding="utf-8"))

    for surface_id in [
        "derived::ehp",
        "derived::ehp_ep",
        "derived::edamage",
        "derived::edamage_ep",
        "derived::eecon",
        "derived::eecon_ep",
        "derived::eecon.base_coin_income",
        "derived::economy.income.coins",
    ]:
        assert surface_id in statbook["rows"], f"missing runtime-published surface {surface_id}"

    assert statbook["rows"]["derived::ehp"]["final_value"] == optimizer["objectives"]["ehp"]["score"]
    assert statbook["rows"]["derived::edamage"]["final_value"] == optimizer["objectives"]["edamage"]["score"]
    assert statbook["rows"]["derived::eecon"]["final_value"] == optimizer["objectives"]["eecon"]["score"]
    assert statbook["rows"]["derived::economy.income.coins"]["schema"]["unit"] == "coins_income_proxy"
    assert statbook["rows"]["derived::economy.income.coins"]["contributors"][0]["source_name"] == "derived::eecon.base_coin_income"


def test_default_runtime_validation_does_not_publish_unset_manual_income_surfaces():
    out_dir = cached_run_stats_output()
    statbook = json.loads((out_dir / "statbook.json").read_text(encoding="utf-8"))

    for surface_id in [
        "derived::economy.income.gems",
        "derived::economy.income.stones",
        "derived::economy.income.medals",
        "derived::economy.income.keys",
        "derived::economy.income.shards",
        "derived::economy.income.bits",
    ]:
        assert surface_id not in statbook["rows"]
