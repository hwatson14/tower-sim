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
