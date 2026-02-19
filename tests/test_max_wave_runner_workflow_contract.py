from __future__ import annotations

from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/max_wave_runner.yml")


def test_max_wave_workflow_invokes_runner_module_with_explicit_hermetic_paths() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "python -m tower_sim.run.runner" in text
    assert "--spec /workspace/tower-sim/fixtures/specs/max_wave.yaml" in text
    assert "--ids /workspace/tower-sim/tests/fixtures/tower-sim-data/_IDS.csv" in text
    assert "--output out/runner_output.json" not in text


def test_max_wave_workflow_extracts_max_wave_result_payload_from_task_envelope() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'if payload.get("task") != "MAX_WAVE":' in text
    assert 'result = payload.get("result")' in text
    assert 'Path("out/runner_output.json").write_text' in text


def test_max_wave_workflow_uploads_artifacts_without_committing_generated_outputs() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "- name: Upload runner output artifact" in text
    assert "- name: Commit latest max-wave artifacts to main" not in text
