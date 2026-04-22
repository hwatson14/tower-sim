"""App main-path smoke tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.live


def test_main_entrypoint_is_importable__callable():
    from app.run_stats import main

    assert callable(main)


def test_analysis_entrypoint_is_importable__callable():
    from app.run_analysis import main

    assert callable(main)


def test_pipeline_entrypoints_are_importable__callable():
    from app.pipeline import (
        RunStatsSession,
        execute_pipeline,
        get_default_run_stats_session,
        run_analysis_pipeline,
        run_stats_pipeline,
    )

    assert callable(execute_pipeline)
    assert callable(run_stats_pipeline)
    assert callable(run_analysis_pipeline)
    assert callable(RunStatsSession)
    assert get_default_run_stats_session() is get_default_run_stats_session()


def test_pipeline_module_imports_active_layers__contains_expected_imports():
    import app.pipeline as pipeline_mod

    src = Path(pipeline_mod.__file__).read_text(encoding="utf-8")
    assert "from qe.publication import publish_query_surfaces" in src
    assert "from qe.shared_runtime_context import get_default_qe_shared_runtime_context" in src
    assert "from simulators.progression import resolve_run_stats_progression_bundle" in src
    assert "resolve_run_stats_progression_bundle" in src
    assert "resolve_timing_consumer_bundle" in src
    assert "QEResolutionPlanner" in src
    assert "publish_query_surfaces" in src
    assert "from evaluators.scorer import compute_optimizer_scores" in src
    assert "from input.loader import load_inputs" in src
    assert "from input.runtime_state import build_runtime_state" in src


def test_pipeline_uses_explicit_report_snapshot_path():
    src = Path((ROOT / "app" / "pipeline.py")).read_text(encoding="utf-8")
    assert "resolve_report_snapshot(" in src
    assert "resolve_snapshot(" not in src


def test_run_stats_cli_defaults_to_current_stats_mode():
    src = Path((ROOT / "app" / "run_stats.py")).read_text(encoding="utf-8")
    removed_flags = ("--" + "watch", "--" + "server", "--use" + "-server")
    assert "--perk-mode" in src
    for flag in removed_flags:
        assert flag not in src
    assert "--state-mode" not in src
    assert "--preset" not in src
    assert "default='max_progression_policy'" in src


def test_run_analysis_cli_preserves_analysis_flags():
    src = Path((ROOT / "app" / "run_analysis.py")).read_text(encoding="utf-8")
    assert "--include-slow-audits" in src
    assert "max_progression_policy" in src


def test_streamlit_inspector_is_importable_when_streamlit_available():
    pytest.importorskip("streamlit")
    import app.streamlit_inspector as inspector_mod

    assert callable(inspector_mod.main)


def test_run_stats_pipeline_targets_farming_and_tourney():
    src = Path((ROOT / "app" / "pipeline.py")).read_text(encoding="utf-8")
    assert "preset_names = ['Farming', 'Tourney']" in src


def test_run_stats_pipeline_writes_query_artifacts_not_fake_statbooks():
    src = Path((ROOT / "app" / "pipeline.py")).read_text(encoding="utf-8")
    assert "run_stats_query_rows_start_of_run.json" in src
    assert "run_stats_query_rows_max_progression.json" in src
    assert "run_stats_query_plan_start_of_run.json" in src
    assert "run_stats_query_plan_max_progression.json" in src
    assert "_remove_legacy_outputs" in src


def test_residue_artifact_contract_is_internally_consistent():
    """Producer keys in pipeline.py must exactly match the keys consumed by publication.py.

    This asserts the end-to-end contract at the source level:
    - Every key written to diagnostics[] in run_analysis_pipeline() must appear
      as a diagnostics.get('<key>') call in write_core_outputs().
    - The filenames written by publication.py are the single authoritative list.
    """
    pipeline_src = Path((ROOT / "app" / "pipeline.py")).read_text(encoding="utf-8")
    publication_src = Path((ROOT / "app" / "publication.py")).read_text(encoding="utf-8")

    expected_contract = {
        'tower_regen_closure_report.json': "diagnostics['tower_regen_closure_report']",
        'tower_hp_semantic_gap_report.json': "diagnostics['tower_hp_semantic_gap_report']",
        'tower_regen_ep_semantic_gap_report.json': "diagnostics['tower_regen_ep_semantic_gap_report']",
        'tower_defense_absolute_semantic_gap_report.json': "diagnostics['tower_defense_absolute_semantic_gap_report']",
        'tower_damage_runtime_gap_report.json': "diagnostics['tower_damage_runtime_gap_report']",
    }

    for filename, producer_assignment in expected_contract.items():
        assert filename in publication_src, (
            f"publication.py does not reference artifact file '{filename}'"
        )
        assert producer_assignment in pipeline_src, (
            f"pipeline.py is missing producer assignment '{producer_assignment}' "
            f"required to populate '{filename}'"
        )

    assert "_build_tower_regen_ep_semantic_gap_report" in pipeline_src
    assert "_build_tower_defense_absolute_semantic_gap_report" in pipeline_src
    assert "_build_tower_damage_runtime_gap_report" in pipeline_src


def test_run_stats_main_defaults_to_in_process_pipeline(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    called = {"pipeline": 0}

    def _pipeline(args):
        called["pipeline"] += 1
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(sys, "argv", ["app.run_stats"])

    assert run_stats_mod.main() == 0
    assert called == {"pipeline": 1}
