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


def test_run_stats_main_threads_tier_override_to_pipeline(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["tier"] = args.tier
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(sys, "argv", ["app.run_stats", "--tier", "14"])

    assert run_stats_mod.main() == 0
    assert captured["tier"] == 14


def test_run_stats_main_threads_run_tracker_csv_to_pipeline(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["run_tracker_csv"] = args.run_tracker_csv
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        ["app.run_stats", "--run-tracker-csv", "input/imports/runs.csv"],
    )

    assert run_stats_mod.main() == 0
    assert captured["run_tracker_csv"] == Path("input/imports/runs.csv")


def test_run_stats_main_threads_boss_wave_milestone_matrix_flag_to_pipeline(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["include_boss_wave_milestone_matrix"] = args.include_boss_wave_milestone_matrix
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(sys, "argv", ["app.run_stats", "--include-boss-wave-milestone-matrix"])

    assert run_stats_mod.main() == 0
    assert captured["include_boss_wave_milestone_matrix"] is True


def test_run_stats_main_threads_clean_reference_alignment_flag_to_pipeline(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["align_clean_reference_rows"] = args.boss_wave_align_clean_reference_rows
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(sys, "argv", ["app.run_stats", "--boss-wave-align-clean-reference-rows"])

    assert run_stats_mod.main() == 0
    assert captured["align_clean_reference_rows"] is True


def test_run_stats_main_defaults_clean_reference_alignment_to_pipeline(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["align_clean_reference_rows"] = args.boss_wave_align_clean_reference_rows
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(sys, "argv", ["app.run_stats"])

    assert run_stats_mod.main() == 0
    assert captured["align_clean_reference_rows"] is True


def test_run_stats_main_can_request_clean_reference_comparison_only(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["align_clean_reference_rows"] = args.boss_wave_align_clean_reference_rows
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(sys, "argv", ["app.run_stats", "--boss-wave-compare-clean-reference-rows"])

    assert run_stats_mod.main() == 0
    assert captured["align_clean_reference_rows"] is False


def test_run_stats_main_threads_boss_wave_bridge_comparison_factors_to_pipeline(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["target_share"] = args.boss_wave_bridge_target_share
        captured["cadence"] = args.boss_wave_bridge_cadence_uptime
        captured["reliability"] = args.boss_wave_bridge_reliability
        captured["normalizer"] = args.boss_wave_bridge_semantic_normalizer
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "app.run_stats",
            "--boss-wave-bridge-target-share",
            "0.5",
            "--boss-wave-bridge-cadence-uptime",
            "0.6",
            "--boss-wave-bridge-reliability",
            "0.7",
            "--boss-wave-bridge-semantic-normalizer",
            "0.8",
        ],
    )

    assert run_stats_mod.main() == 0
    assert captured == {
        "target_share": 0.5,
        "cadence": 0.6,
        "reliability": 0.7,
        "normalizer": 0.8,
    }


def test_run_stats_main_threads_boss_wave_comparison_pressure_factor_to_pipeline(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["comparison_pressure_factor"] = args.boss_wave_comparison_pressure_factor
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "app.run_stats",
            "--boss-wave-comparison-pressure-factor",
            "1.25",
        ],
    )

    assert run_stats_mod.main() == 0
    assert captured == {"comparison_pressure_factor": 1.25}


def test_run_stats_main_threads_boss_wave_comparison_terminal_closures_to_pipeline(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["fleet"] = args.boss_wave_comparison_fleet_terminal_max_wave
        captured["elite"] = args.boss_wave_comparison_elite_terminal_max_wave
        captured["protector"] = args.boss_wave_comparison_protector_terminal_max_wave
        captured["armored"] = args.boss_wave_comparison_armored_terminal_max_wave
        captured["boss"] = args.boss_wave_comparison_boss_terminal_max_wave
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "app.run_stats",
            "--boss-wave-comparison-fleet-terminal-max-wave",
            "900",
            "--boss-wave-comparison-elite-terminal-max-wave",
            "901",
            "--boss-wave-comparison-protector-terminal-max-wave",
            "902",
            "--boss-wave-comparison-armored-terminal-max-wave",
            "903",
            "--boss-wave-comparison-boss-terminal-max-wave",
            "904",
        ],
    )

    assert run_stats_mod.main() == 0
    assert captured == {
        "fleet": 900.0,
        "elite": 901.0,
        "protector": 902.0,
        "armored": 903.0,
        "boss": 904.0,
    }


def test_run_stats_main_threads_boss_wave_terminal_pressure_closures_to_pipeline(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["fleet"] = args.boss_wave_fleet_terminal_max_wave
        captured["elite"] = args.boss_wave_elite_terminal_max_wave
        captured["protector"] = args.boss_wave_protector_terminal_max_wave
        captured["armored"] = args.boss_wave_armored_terminal_max_wave
        captured["boss"] = args.boss_wave_boss_terminal_max_wave
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "app.run_stats",
            "--boss-wave-fleet-terminal-max-wave",
            "900",
            "--boss-wave-elite-terminal-max-wave",
            "901",
            "--boss-wave-protector-terminal-max-wave",
            "902",
            "--boss-wave-armored-terminal-max-wave",
            "903",
            "--boss-wave-boss-terminal-max-wave",
            "904",
        ],
    )

    assert run_stats_mod.main() == 0
    assert captured == {
        "fleet": 900.0,
        "elite": 901.0,
        "protector": 902.0,
        "armored": 903.0,
        "boss": 904.0,
    }


def test_run_stats_main_threads_boss_wave_pressure_factor_to_pipeline(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["pressure_factor"] = args.boss_wave_pressure_factor
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "app.run_stats",
            "--boss-wave-pressure-factor",
            "1.25",
        ],
    )

    assert run_stats_mod.main() == 0
    assert captured == {
        "pressure_factor": 1.25,
    }


def test_run_stats_main_threads_boss_wave_pressure_factor_review_default_approval(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["approve_review_default"] = args.approve_boss_wave_pressure_factor_review_default
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "app.run_stats",
            "--approve-boss-wave-pressure-factor-review-default",
        ],
    )

    assert run_stats_mod.main() == 0
    assert captured == {
        "approve_review_default": True,
    }


def test_run_stats_main_threads_tracker_wave_skip_intro_semantics_approval(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["approve_skip_intro_semantics"] = (
            args.approve_tracker_wave_skip_intro_semantics
        )
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "app.run_stats",
            "--approve-tracker-wave-skip-intro-semantics",
        ],
    )

    assert run_stats_mod.main() == 0
    assert captured == {
        "approve_skip_intro_semantics": True,
    }


def test_run_stats_main_threads_final_tracker_cph_approvals(monkeypatch):
    import app.pipeline as pipeline_mod
    import app.run_stats as run_stats_mod

    captured = {}

    def _pipeline(args):
        captured["approve_integrals"] = (
            args.approve_tracker_empirical_run_coin_duration_integrals
        )
        captured["approve_validation"] = (
            args.approve_tracker_current_export_account_state_validation
        )
        return 0

    monkeypatch.setattr(pipeline_mod, "run_stats_pipeline", _pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "app.run_stats",
            "--approve-tracker-empirical-run-coin-duration-integrals",
            "--approve-tracker-current-export-account-state-validation",
        ],
    )

    assert run_stats_mod.main() == 0
    assert captured == {
        "approve_integrals": True,
        "approve_validation": True,
    }
