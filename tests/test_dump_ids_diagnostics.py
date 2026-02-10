from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_dump_ids_diagnostics(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ids_path = repo_root / "tests" / "fixtures" / "tower-sim-data" / "_IDS.csv"
    output_dir = tmp_path / "audit"
    output_path = output_dir / "account_snapshot.json"
    summary_path = output_dir / "account_snapshot.summary.json"
    diff_path = output_dir / "account_snapshot.diff.json"
    base_components_path = output_dir / "base_stats_components.json"
    inventory_components_path = output_dir / "inventory_components.json"
    run_stats_path = output_dir / "run_stats.json"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "dump_ids_diagnostics.py"),
            "--ids-path",
            str(ids_path),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert output_path.exists()
    assert summary_path.exists()
    assert base_components_path.exists()
    assert inventory_components_path.exists()
    assert run_stats_path.exists()
    assert not diff_path.exists()
    payload = json.loads(output_path.read_text())
    assert payload["schema_version"] == 4
    assert isinstance(payload["created_utc"], str)
    assert payload["created_utc"]
    assert "git_sha" in payload
    assert payload["ids_path"] == str(ids_path)
    assert "missing_sections" in payload
    assert isinstance(payload["missing_sections"], list)
    assert "base_stats" in payload
    assert "inventory" in payload
    assert "loadout" in payload
    assert "snapshot" in payload
    assert isinstance(payload["base_stats"], list)
    assert payload["base_stats"]
    assert "cards" in payload["inventory"]
    assert "modules" in payload["inventory"]
    assert "ultimate_weapons" in payload["inventory"]
    assert "workshop" in payload["inventory"]
    assert "themes_songs" in payload["inventory"]
    assert "guardians" in payload["inventory"]
    assert "player_stuff" in payload["inventory"]
    assert payload["inventory"]["themes_songs"] is None
    assert payload["inventory"]["guardians"] is None
    assert payload["inventory"]["player_stuff"] is None
    assert payload["loadout"]["preset_name"]
    assert "themes_songs" not in payload["missing_sections"]
    assert "guardians" not in payload["missing_sections"]
    assert "player_stuff" not in payload["missing_sections"]
    for row in payload["base_stats"]:
        assert "stat_id" in row
        assert "phase" in row
        assert "base_value" in row
        assert "final_value" in row
        assert "provenance" in row
    assert "Wrote" in result.stdout


    base_components = json.loads(base_components_path.read_text())
    assert "themes_songs" in base_components
    assert "labs" in base_components
    assert "ultimate_weapons" in base_components
    assert "vault_v2" in base_components
    assert "relics" in base_components
    assert "workshop_coin_levels" in base_components
    assert "enhancements" in base_components
    assert "guardians" in base_components
    assert "bots" in base_components

    inventory_components = json.loads(inventory_components_path.read_text())
    assert "cards_mastery_inventory" in inventory_components
    assert "card_presets" in inventory_components
    assert "modules_inventory" in inventory_components
    assert "module_presets" in inventory_components
    assert "shard_allocation" in inventory_components

    run_stats = json.loads(run_stats_path.read_text())
    assert isinstance(run_stats["rows"], list)
    assert "missing" in run_stats
    assert "fail_closed" in run_stats

    summary = json.loads(summary_path.read_text())
    assert summary["ids_path"] == str(ids_path)
    assert summary["labs_count"] >= 1

    output_dir_raw = tmp_path / "audit_raw"
    output_path_raw = output_dir_raw / "account_snapshot.json"
    result_raw = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "dump_ids_diagnostics.py"),
            "--ids-path",
            str(ids_path),
            "--output-dir",
            str(output_dir_raw),
            "--include-raw",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    payload_raw = json.loads(output_path_raw.read_text())
    for key in ("themes_songs", "guardians", "player_stuff"):
        assert key in payload_raw["inventory"]
        assert payload_raw["inventory"][key] is None or isinstance(
            payload_raw["inventory"][key], (list, dict)
        )
    assert isinstance(payload_raw["missing_sections"], list)
    assert "Wrote" in result_raw.stdout
