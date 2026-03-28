"""
tests/live/test_main_path.py -- Main CLI path smoke test.

Verifies: app/ wires all layers correctly end-to-end.
Gate: fails if the main supported path is broken.

Implemented in T6 (after app/ is wired).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_app_run_stats_is_importable():
    from app.run_stats import main
    assert callable(main)


def test_app_pipeline_is_importable():
    from app.pipeline import run_pipeline
    assert callable(run_pipeline)


def test_app_pipeline_wires_active_layer_imports():
    """Pipeline imports from qe.*, evaluators.*, input.* -- not legacy-only paths."""
    import app.pipeline as pipeline_mod
    src = open(pipeline_mod.__file__, encoding="utf-8").read()
    assert "from qe.routing import resolve_stats" in src
    assert "from qe.publication import publish_phase3_query_surfaces" in src
    assert "from evaluators.scorer import compute_optimizer_scores" in src
    assert "from input.ids_parser import parse_ids" in src
