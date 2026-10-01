from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_cli_smoke_writes_validation_report(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    completed = subprocess.run(
        [sys.executable, "-m", "app.tools.module_reroll", "--repo-root", str(ROOT), "--run-smoke", "current_as", "--output", str(output)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "wrote experimental" in completed.stdout
    report = json.loads(output.read_text())
    assert report["loaded_family_counts"]["Core"] == 26
    assert report["rarity_probabilities"]["Ancestral"] == 0.003
    assert report["lock_costs"]["5"] == 1600
    assert report["duplicate_policy"]["certification_status"] == "assumption_uncertified"
    assert "kb/modules/contracts/module-reroll-cost-contract-r61.yaml" in report["source_contracts"]
    assert report["anchor_tail_results"]["five_lock_one_target_ancestral_pool_12"]["expected_shards"] == 6_400_000
    assert report["certification"]["mechanics_certified"] is False


def test_cli_wires_account_state_ban_labs_and_selected_bans(tmp_path: Path) -> None:
    account_state = tmp_path / "account_state.json"
    account_state.write_text(json.dumps({"labs": {
        "Cannon Effect Bans": 2,
        "Armor Effect Bans": 0,
        "Generator Effect Bans": 0,
        "Core Effect Bans": 1,
    }}))
    selected_bans = tmp_path / "selected_bans.json"
    selected_bans.write_text(json.dumps({"Cannon": ["Attack Speed", "Crit Factor"], "Core": ["Chrono Field - Duration"]}))
    output = tmp_path / "report_with_bans.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "app.tools.module_reroll",
            "--repo-root",
            str(ROOT),
            "--account-state",
            str(account_state),
            "--selected-bans",
            str(selected_bans),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    report = json.loads(output.read_text())
    assert report["ban_labs"]["capacities"]["Cannon"]["level"] == 2
    assert report["ban_labs"]["capacities"]["Core"]["level"] == 1
    assert report["ban_labs"]["selected_ban_effect_ids"]["Cannon"] == ["attack_speed", "crit.factor"]
    assert report["ban_labs"]["selected_ban_effect_ids"]["Core"] == ["chrono_field.duration"]
