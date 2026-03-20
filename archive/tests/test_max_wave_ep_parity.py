from __future__ import annotations

import json
from pathlib import Path

import pytest

from tower_sim.audit import max_wave_ep_parity
from tower_sim.loaders.ep_export_loader import EPExportDataset, EPExportRow


def _write_runner(path: Path, w_max: float, tolerance: float = 0.10) -> None:
    path.write_text(
        json.dumps(
            {
                "w_max": w_max,
                "assumptions_manifest": {
                    "parity_tolerances": {"wmax_wave_relative": tolerance}
                },
            }
        ),
        encoding="utf-8",
    )


def _dataset_with_targets() -> EPExportDataset:
    rows = (
        EPExportRow(
            suite="ehp",
            key="max_wave",
            label="Max Wave",
            value_raw="100",
            value_numeric=100.0,
            preset="farming",
            source_ref="ep_sheet:eHP!CG5",
            verification_path="ep_formula.eval.ehp",
            has_definitive_formula=True,
        ),
    )
    return EPExportDataset(rows=rows, verification_presets={"ehp": "farming"})


def test_validate_runner_against_ep_export_validated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    runner_output = tmp_path / "runner.json"
    _write_runner(runner_output, 100)

    monkeypatch.setattr(max_wave_ep_parity, "load_ep_export_dataset", lambda: _dataset_with_targets())

    result = max_wave_ep_parity.validate_runner_against_ep_export(
        runner_output_path=runner_output,
        suite="ehp",
    )

    assert result["status"] == "validated"
    assert result["delta"] == 0.0


def test_validate_runner_against_ep_export_skips_missing_targets_when_allowed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner_output = tmp_path / "runner.json"
    _write_runner(runner_output, 100)

    monkeypatch.setattr(max_wave_ep_parity, "load_ep_export_dataset", lambda: EPExportDataset(rows=(), verification_presets={}))

    result = max_wave_ep_parity.validate_runner_against_ep_export(
        runner_output_path=runner_output,
        suite="ehp",
        allow_missing_targets=True,
    )

    assert result["status"] == "skipped_missing_targets"


def test_validate_runner_against_ep_export_fails_on_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner_output = tmp_path / "runner.json"
    _write_runner(runner_output, 120)

    monkeypatch.setattr(max_wave_ep_parity, "load_ep_export_dataset", lambda: _dataset_with_targets())

    with pytest.raises(ValueError, match="parity mismatch"):
        max_wave_ep_parity.validate_runner_against_ep_export(
            runner_output_path=runner_output,
            suite="ehp",
            tolerance=0.0,
        )


def test_validate_runner_against_ep_export_uses_manifest_tolerance_when_unspecified(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner_output = tmp_path / "runner.json"
    _write_runner(runner_output, 105, tolerance=5.0)

    monkeypatch.setattr(max_wave_ep_parity, "load_ep_export_dataset", lambda: _dataset_with_targets())

    result = max_wave_ep_parity.validate_runner_against_ep_export(
        runner_output_path=runner_output,
        suite="ehp",
    )

    assert result["status"] == "validated"
    assert result["tolerance"] == 5.0


def test_validate_runner_against_ep_export_fails_when_manifest_tolerance_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    runner_output = tmp_path / "runner.json"
    runner_output.write_text(json.dumps({"w_max": 100.0}), encoding="utf-8")

    monkeypatch.setattr(max_wave_ep_parity, "load_ep_export_dataset", lambda: _dataset_with_targets())

    with pytest.raises(ValueError, match="assumptions_manifest"):
        max_wave_ep_parity.validate_runner_against_ep_export(
            runner_output_path=runner_output,
            suite="ehp",
        )
