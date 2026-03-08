from __future__ import annotations

from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/max_wave_runner.yml")


def test_max_wave_workflow_invokes_runner_module_with_explicit_hermetic_paths() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "python -m tower_sim.run.runner" in text
    assert '--spec "${{ github.workspace }}/fixtures/specs/max_wave.yaml"' in text
    assert '--ids "${{ github.workspace }}/tests/fixtures/tower-sim-data/_IDS.csv"' in text
    assert "/workspace/tower-sim/" not in text


def test_max_wave_workflow_validates_canonical_runner_output() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'Path("out/max_wave_runner/max_wave_latest.json")' in text
    assert 'required = {"evaluator", "fail_closed", "missing", "w_max", "diagnostics"}' in text


def test_max_wave_workflow_uploads_artifacts_without_committing_generated_outputs() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "- name: Upload runner output artifact" in text
    assert "- name: Commit latest max-wave artifacts to main" not in text


def test_max_wave_workflow_commits_only_canonical_latest_outputs() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "git add out/max_wave_runner/runner_output_latest.json out/max_wave_runner/max_wave_latest.json" in text


def test_max_wave_workflow_exports_lineage_from_stat_lineage_manifest() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "--manifest out/stat_lineage_manifest.json" in text
    assert "--manifest out/lineage_manifest_latest.json" not in text


def test_max_wave_workflow_runs_wiring_health_check_with_canonical_manifest() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "python -m tower_sim.audit.wiring_health_check" in text
    assert "--lineage-manifest out/stat_lineage_manifest.json" in text


def test_max_wave_workflow_emits_observed_contributors_into_stat_lineage_manifest() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "observed_contributors_by_stat_input_id" in text
    assert "Runner diagnostics missing observed_contributors_by_stat_input_id." in text
