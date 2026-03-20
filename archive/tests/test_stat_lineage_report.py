from __future__ import annotations

import json
from pathlib import Path

import pytest

from tower_sim.audit.stat_lineage_report import load_manifest, summarize_manifest


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_summarize_manifest_counts_missing_pairs_and_required_gaps(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(
        manifest_path,
        {
            "required_max_wave_stat_input_ids": ["tower_hp", "tower_regen"],
            "status_lists": {
                "tower_hp": {
                    "wired_up": ["workshop"],
                    "not_expected_to_be_wired_up": ["bc"],
                    "still_requires_wiring_up": ["card", "perk"],
                },
                "tower_regen": {
                    "wired_up": ["workshop"],
                    "not_expected_to_be_wired_up": ["bc"],
                    "still_requires_wiring_up": [],
                },
                "wall_hp": {
                    "wired_up": ["workshop"],
                    "not_expected_to_be_wired_up": ["bc"],
                    "still_requires_wiring_up": ["perk"],
                },
            },
        },
    )

    summary = summarize_manifest(load_manifest(manifest_path))

    assert summary["stats_total"] == 3
    assert summary["stats_with_missing"] == 2
    assert summary["total_missing_pairs"] == 3
    assert summary["missing_by_contributor"] == {"card": 1, "perk": 2}
    assert summary["required_max_wave_gap_count"] == 1
    assert summary["required_max_wave_gaps"] == {"tower_hp": ["card", "perk"]}
    assert len(summary["full_table"]) == 3
    tower_hp_row = next(item for item in summary["full_table"] if item["stat_id"] == "tower_hp")
    assert tower_hp_row["required_max_wave"] is True
    assert tower_hp_row["contributors"]["workshop"] == "wired"
    assert tower_hp_row["contributors"]["card"] == "missing"
    assert tower_hp_row["contributors"]["bc"] == "not_expected"


def test_load_manifest_fails_closed_when_required_key_missing(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(
        manifest_path,
        {
            "status_lists": {},
        },
    )

    with pytest.raises(ValueError, match="required_max_wave_stat_input_ids"):
        load_manifest(manifest_path)


def test_load_manifest_fails_closed_when_status_shape_is_invalid(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(
        manifest_path,
        {
            "required_max_wave_stat_input_ids": [],
            "status_lists": {
                "tower_hp": {
                    "wired_up": [],
                    "not_expected_to_be_wired_up": [],
                }
            },
        },
    )

    with pytest.raises(ValueError, match="still_requires_wiring_up"):
        load_manifest(manifest_path)


def test_summarize_manifest_supports_lineage_manifest_v1_shape(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest_v1.json"
    _write_manifest(
        manifest_path,
        {
            "schema": "lineage_manifest.v1",
            "required_max_wave_stat_input_ids": ["tower_hp"],
            "stats": {
                "tower_hp": [
                    {
                        "contributor": "workshop",
                        "reaches_stat_input": True,
                        "exclusion_reason": None,
                    },
                    {
                        "contributor": "card",
                        "reaches_stat_input": False,
                        "exclusion_reason": "excluded:not_wired_to_canonical_stat_input",
                    },
                    {
                        "contributor": "uw",
                        "reaches_stat_input": False,
                        "exclusion_reason": "excluded:no_authoritative_uw_mapping_for_stat",
                    },
                ],
            },
        },
    )

    summary = summarize_manifest(load_manifest(manifest_path))

    assert summary["missing_by_contributor"] == {"card": 1}
    assert summary["required_max_wave_gap_count"] == 1
    assert summary["required_max_wave_gaps"] == {"tower_hp": ["card"]}
    assert summary["contributor_totals"]["workshop"]["status"] == "complete"
    assert summary["contributor_totals"]["card"]["status"] == "not_wired"
    assert summary["contributor_totals"]["uw"]["status"] == "excluded"
    assert summary["focus_section_status"]["enhancement"]["status"] == "not_tracked_in_lineage_contract"
    assert summary["focus_section_status"]["bot"]["status"] == "not_tracked_in_lineage_contract"
    assert len(summary["full_table"]) == 1
    row = summary["full_table"][0]
    assert row["stat_id"] == "tower_hp"
    assert row["contributors"]["workshop"] == "wired"
    assert row["contributors"]["card"] == "missing"
    assert row["contributors"]["uw"] == "not_expected"


def test_summarize_manifest_reports_observed_vs_declared_mismatch(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest_observed.json"
    _write_manifest(
        manifest_path,
        {
            "required_max_wave_stat_input_ids": ["tower_hp"],
            "status_lists": {
                "tower_hp": {
                    "wired_up": ["card"],
                    "not_expected_to_be_wired_up": [],
                    "still_requires_wiring_up": [],
                },
            },
            "observed_contributors_by_stat_input_id": {
                "tower_hp": ["card", "lab"],
            },
        },
    )

    summary = summarize_manifest(load_manifest(manifest_path))

    assert summary["observed_vs_declared_mismatch_count"] == 1
    assert summary["observed_vs_declared_mismatches"]["tower_hp"]["observed_but_not_declared"] == ["lab"]
