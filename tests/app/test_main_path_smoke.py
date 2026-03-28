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
    from app.pipeline import run_pipeline

    assert callable(run_pipeline)


def test_pipeline_module_imports_active_layers__contains_expected_imports():
    import app.pipeline as pipeline_mod

    src = Path(pipeline_mod.__file__).read_text(encoding="utf-8")
    assert "from qe.routing import resolve_stats" in src
    assert "from qe.publication import publish_phase3_query_surfaces" in src
    assert "from evaluators.scorer import compute_optimizer_scores" in src
    assert "from input.ids_parser import parse_ids" in src
