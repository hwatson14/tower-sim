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
    ids_raw_index_path = output_dir / "ids_raw_index.json"
    compiled_stat_inputs_path = output_dir / "compiled_stat_inputs.json"
    stat_engine_path = output_dir / "stat_engine.json"
    resolved_problem_spec_path = output_dir / "resolved_problem_spec.json"
    max_wave_path = output_dir / "max_wave.json"
    stage_1_path = output_dir / "stage_1_base_no_respec.json"
    stage_2_path = output_dir / "stage_2_base_with_respec.json"
    stage_3_path = output_dir / "stage_3_with_loadout.json"
    stage_4_path = output_dir / "stage_4_with_battle_conditions.json"
    stage_5_path = output_dir / "stage_5_end_of_run.json"
    diagnostics_path = output_dir / "diagnostics.json"

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
    assert ids_raw_index_path.exists()
    assert compiled_stat_inputs_path.exists()
    assert stat_engine_path.exists()
    assert resolved_problem_spec_path.exists()
    assert max_wave_path.exists()
    assert stage_1_path.exists()
    assert stage_2_path.exists()
    assert stage_3_path.exists()
    assert stage_4_path.exists()
    assert stage_5_path.exists()
    assert diagnostics_path.exists()
    assert not diff_path.exists()
    payload = json.loads(output_path.read_text())
    assert payload["schema_version"] == 5
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
    assert "pipeline" in payload
    assert "ids_raw_index" in payload["pipeline"]
    assert "compiled_stat_inputs" in payload["pipeline"]
    assert "stat_engine" in payload["pipeline"]
    assert "staged_outputs" in payload
    assert "stage_1_base_no_respec" in payload["staged_outputs"]
    assert "stage_2_base_with_respec" in payload["staged_outputs"]
    assert "stage_3_with_loadout" in payload["staged_outputs"]
    assert "stage_4_with_battle_conditions" in payload["staged_outputs"]
    assert "stage_5_end_of_run" in payload["staged_outputs"]
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

    stage_1 = json.loads(stage_1_path.read_text())
    stage_2 = json.loads(stage_2_path.read_text())
    stage_3 = json.loads(stage_3_path.read_text())
    stage_4 = json.loads(stage_4_path.read_text())
    stage_5 = json.loads(stage_5_path.read_text())
    diagnostics = json.loads(diagnostics_path.read_text())
    assert stage_1["name"] == "locked_base"
    assert stage_2["name"] == "gem_respec_base"
    assert stage_3["name"] == "loadout"
    assert stage_4["name"] == "battle_conditions"
    assert stage_5["name"] == "end_of_run"
    assert diagnostics["ids_path"] == str(ids_path)
    assert diagnostics["schema_version"] == 5
    assert "stages" in diagnostics
    assert "run_stats" in diagnostics
    assert "max_wave" in diagnostics

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


def test_dump_ids_diagnostics_runs_without_pythonpath_env(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ids_path = repo_root / "tests" / "fixtures" / "tower-sim-data" / "_IDS.csv"
    output_dir = tmp_path / "audit_no_pythonpath"
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
    )

    assert (output_dir / "account_snapshot.json").exists()
    assert (output_dir / "stage_1_base_no_respec.json").exists()
    assert (output_dir / "diagnostics.json").exists()
    assert "Wrote" in result.stdout


def test_dump_ids_diagnostics_writes_yaml_artifacts(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    ids_path = repo_root / "tests" / "fixtures" / "tower-sim-data" / "_IDS.csv"
    output_dir = tmp_path / "audit_yaml"

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "dump_ids_diagnostics.py"),
            "--ids-path",
            str(ids_path),
            "--output-dir",
            str(output_dir),
            "--write-yaml",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert (output_dir / "account_snapshot.yml").exists()
    assert (output_dir / "diagnostics.yml").exists()
    assert "Wrote" in result.stdout
