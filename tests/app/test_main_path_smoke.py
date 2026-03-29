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


def test_pipeline_entrypoint_is_importable__callable():
    from app.pipeline import execute_pipeline, run_pipeline

    assert callable(execute_pipeline)
    assert callable(run_pipeline)


def test_pipeline_module_imports_active_layers__contains_expected_imports():
    import app.pipeline as pipeline_mod

    src = Path(pipeline_mod.__file__).read_text(encoding="utf-8")
    assert "from qe.publication import publish_phase3_query_surfaces" in src
    assert "from qe.shared_runtime_context import get_default_qe_shared_runtime_context" in src
    assert "from simulators.progression import resolve_run_stats_progression_bundle" in src
    assert "from input.loader import load_inputs" in src


def test_cli_exposes_explicit_perk_mode_argument():
    src = Path((ROOT / "app" / "run_stats.py")).read_text(encoding="utf-8")
    assert "--perk-mode" in src
    assert "max_progression_policy" in src


def test_cli_exposes_slow_audits_flag():
    src = Path((ROOT / "app" / "run_analysis.py")).read_text(encoding="utf-8")
    assert "--include-slow-audits" in src


def test_streamlit_inspector_is_importable_when_streamlit_available():
    pytest.importorskip("streamlit")
    import app.streamlit_inspector as inspector_mod

    assert callable(inspector_mod.main)


def test_module_substat_rarity_inference_uses_kb_values_and_assist_cap():
    import app.streamlit_inspector as inspector_mod

    primary_rarity = inspector_mod._infer_module_substat_rarity(
        'armor',
        {'name': 'Knockback Force', 'raw_token': '0.9'},
        role='primary',
        slot_state=None,
    )
    assist_rarity = inspector_mod._infer_module_substat_rarity(
        'armor',
        {'name': 'Knockback Force', 'raw_token': '0.9'},
        role='assist',
        slot_state={'rarity_cap': 'Epic'},
    )
    alias_rarity = inspector_mod._infer_module_substat_rarity(
        'cannon',
        {'name': 'Critical Factor', 'raw_token': '15'},
        role='primary',
        slot_state=None,
    )

    assert primary_rarity == 'Mythic'
    assert assist_rarity == 'Epic'
    assert alias_rarity == 'Ancestral'


def test_module_substat_unlock_count_matches_expected_thresholds():
    import app.streamlit_inspector as inspector_mod

    assert inspector_mod._module_substat_unlock_count(1) == 1
    assert inspector_mod._module_substat_unlock_count(40) == 1
    assert inspector_mod._module_substat_unlock_count(41) == 2
    assert inspector_mod._module_substat_unlock_count(100) == 3
    assert inspector_mod._module_substat_unlock_count(101) == 4
    assert inspector_mod._module_substat_unlock_count(165) == 6
    assert inspector_mod._module_substat_unlock_count(241) == 8
