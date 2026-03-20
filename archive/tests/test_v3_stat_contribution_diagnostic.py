from v3.stat_input_compiler import noncanonical_policy_contract
from pathlib import Path
import json
import subprocess
import sys

import pytest

import scripts.v3_stat_contribution_diagnostic as diag_script


def test_v3_stat_contribution_diagnostic_smoke(tmp_path: Path) -> None:
    out = tmp_path / "v3_stat_contribution_diagnostic.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/v3_stat_contribution_diagnostic.py",
            "--ids",
            "tests/fixtures/tower-sim-data/_IDS.csv",
            "--output",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert out.exists()

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["stage"] == "full"
    assert payload["stat_input_count"] > 0
    assert isinstance(payload["missing_systems"], list)
    assert isinstance(payload["dropped_noncanonical"]["rows"], list)
    assert isinstance(payload["dropped_noncanonical_deferred"]["rows"], list)
    assert isinstance(payload["dropped_noncanonical_policy_bounded"]["rows"], list)
    assert payload["dropped_noncanonical_policy"]["ok"] is True
    assert payload["dropped_noncanonical_policy"]["by_family"]
    assert payload["dropped_noncanonical_policy"]["policy"] == noncanonical_policy_contract()
    assert payload["dropped_noncanonical_policy_consistency"]["ok"] is True
    assert payload["dropped_noncanonical_policy_consistency"]["errors"] == []
    assert payload["dropped_noncanonical_partition_consistency"]["ok"] is True
    assert payload["dropped_noncanonical_partition_consistency"]["errors"] == []
    assert payload["dropped_noncanonical_policy"]["policy"]["coverage_complete"] is True
    assert payload["dropped_noncanonical_policy"]["ambiguous_rows"] == []
    assert payload["dropped_noncanonical_policy"]["legacy_format_rows"] == []
    assert isinstance(payload["dropped_kb_unwired"]["rows"], list)
    assert isinstance(payload["routing_gaps"], list)
    assert payload["stat_inputs"]
    assert payload["resolver_trace"]
    assert payload["intermediate_values"]["run_stats_by_phase"]
    assert payload["intermediate_values"]["statbook_rows"]
    assert payload["final_stat_reconciliation"]
    assert "unused_input_rows" in payload["consumed_unused_ledger"]
    assert payload["dependency_graph_audit"]["edge_count"] > 0
    assert payload["contributor_family_coverage_matrix"]
    assert payload["kb_expected_dependency_graph"]["edge_count"] > 0
    assert payload["pipeline_dependency_graph"]["stats"]
    assert payload["kb_vs_pipeline_dependency_report"]["rows"]
    assert payload["kb_vs_runtime_value_audit"]["rows"]
    assert payload["kb_vs_runtime_value_audit"]["summary"]["not_ok"] == 0
    assert payload["phase4_closure_gate"]["ok"] is True
    assert payload["phase4_closure_gate"]["checks"]["missing_systems_zero"] is True
    assert payload["phase4_closure_gate"]["checks"]["routing_gaps_zero"] is True
    assert payload["phase4_closure_gate"]["checks"]["dropped_kb_unwired_zero"] is True
    assert payload["phase4_closure_gate"]["checks"]["dropped_noncanonical_actionable_zero"] is True
    assert payload["phase4_closure_gate"]["checks"]["dropped_noncanonical_policy_bounded"] is True
    assert payload["phase4_closure_gate"]["checks"]["dropped_noncanonical_policy_consistent"] is True
    assert payload["phase4_closure_gate"]["checks"]["dropped_noncanonical_partition_consistent"] is True
    assert payload["phase4_closure_gate"]["checks"]["noncanonical_policy_coverage_complete"] is True
    assert payload["phase4_closure_gate"]["checks"]["dropped_noncanonical_ambiguous_zero"] is True
    assert payload["phase4_closure_gate"]["checks"]["dropped_noncanonical_legacy_format_zero"] is True
    assert payload["phase4_closure_gate"]["checks"]["dependency_not_ok_zero"] is True
    assert payload["phase4_closure_gate"]["checks"]["value_audit_not_ok_zero"] is True

    first = payload["stat_inputs"][0]
    for key in (
        "stat_id",
        "phase",
        "provenance",
        "contributor_family",
        "base_value",
        "additive_value",
        "resolver_decision",
        "resolver_steps",
    ):
        assert key in first


def test_v3_stat_contribution_diagnostic_phase4_gate_enforcement(tmp_path: Path) -> None:
    out = tmp_path / "v3_stat_contribution_diagnostic.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/v3_stat_contribution_diagnostic.py",
            "--ids",
            "tests/fixtures/tower-sim-data/_IDS.csv",
            "--output",
            str(out),
            "--require-phase4-gates",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["phase4_closure_gate"]["ok"] is True


def test_noncanonical_policy_summary_validator_rejects_unknown_family_name() -> None:
    summary = {
        "by_family": {"unknown_family": 1},
        "legacy_format_rows": [],
        "ambiguous_rows": [],
        "unbounded_rows": [],
        "policy": {"families": {"bot_upgrade": {}}, "coverage_complete": True},
        "rows": ["noncanonical_stat_surface:bot_upgrade:bot_table:bot_amplify_bonus"],
    }
    result = diag_script._validate_noncanonical_policy_summary(summary)
    assert result["ok"] is False
    assert any(str(item).startswith("by_family_unknown_names:") for item in result["errors"])


def test_noncanonical_policy_summary_validator_rejects_legacy_format_row() -> None:
    policy = noncanonical_policy_contract()
    summary = {
        "by_family": {"bot_upgrade": 1},
        "legacy_format_rows": [],
        "ambiguous_rows": [],
        "unbounded_rows": [],
        "policy": policy,
        "rows": ["noncanonical_stat_surface:bot_amplify_bonus"],
    }
    result = diag_script._validate_noncanonical_policy_summary(summary)
    assert result["ok"] is False
    assert "row_missing_context:bot_amplify_bonus" in result["errors"]


def test_noncanonical_policy_summary_validator_rejects_prefix_outside_policy() -> None:
    policy = noncanonical_policy_contract()
    summary = {
        "by_family": {"bot_upgrade": 1},
        "legacy_format_rows": [],
        "ambiguous_rows": [],
        "unbounded_rows": [],
        "policy": policy,
        "rows": ["noncanonical_stat_surface:bot_upgrade:uw_section:bot_amplify_bonus"],
    }
    result = diag_script._validate_noncanonical_policy_summary(summary)
    assert result["ok"] is False
    assert "row_prefix_not_in_policy:bot_upgrade:uw_section:bot_amplify_bonus" in result["errors"]


def test_split_noncanonical_rows_partitions_deferred_bounded_and_actionable() -> None:
    rows = [
        "noncanonical_stat_surface:uw_upgrade:uw_alias:uw_black_hole_cooldown",
        "noncanonical_stat_surface:bot_upgrade:bot_table:bot_flame_damage",
        "noncanonical_stat_surface:unlock:base:orb_damage_mult",
        "noncanonical_stat_surface:relic:relics:bot_range",
        "noncanonical_stat_surface:unknown_family:unknown_prefix:unknown_stat",
    ]
    deferred, bounded, actionable = diag_script._split_noncanonical_rows(rows)
    assert deferred == rows[:2]
    assert bounded == rows[2:4]
    assert actionable == rows[4:]


def test_noncanonical_partition_validator_rejects_mismatched_totals() -> None:
    result = diag_script._validate_noncanonical_partition(
        {
            "dropped_noncanonical": {"raw_count": 1},
            "dropped_noncanonical_deferred": {"raw_count": 2},
            "dropped_noncanonical_policy_bounded": {"raw_count": 3},
            "dropped_noncanonical_policy": {"by_family": {"unlock": 7}},
        }
    )
    assert result["ok"] is False
    assert result["errors"] == [
        "noncanonical_partition_raw_count_mismatch:actionable=1:deferred=2:bounded=3:policy_total=7"
    ]


def test_noncanonical_partition_validator_requires_policy_by_family_mapping() -> None:
    result = diag_script._validate_noncanonical_partition(
        {
            "dropped_noncanonical": {"raw_count": 0},
            "dropped_noncanonical_deferred": {"raw_count": 0},
            "dropped_noncanonical_policy_bounded": {"raw_count": 0},
            "dropped_noncanonical_policy": {"by_family": []},
        }
    )
    assert result["ok"] is False
    assert result["errors"] == ["noncanonical_partition_missing_policy_by_family"]


def test_resolve_expected_input_value_rejects_mixed_derived_components() -> None:
    with pytest.raises(ValueError, match="derived_mixed_with_non_derived_components"):
        diag_script._resolve_expected_input_value(
            {
                "derived_value": 1.0,
                "base_value": 2.0,
                "loadout_delta": None,
                "enhancement_multiplier": 1.0,
                "tier_rule_delta": None,
                "tier_rule_multiplier": None,
            }
        )
