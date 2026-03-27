"""
tests/live/test_boundary_contracts.py -- Architecture boundary enforcement gate.

Verifies the active-spine import boundaries that define the post-tranche architecture:
  - app/* does not import root run_stats.py
  - app/* does not import engine.*
  - qe/* does not import forbidden legacy engine authority modules
  - simulators/* does not import engine.*

Gate: fast (no computation). Fails if any boundary is violated.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

APP_DIR = ROOT / "app"
QE_DIR = ROOT / "qe"
SIMULATORS_DIR = ROOT / "simulators"
EVALUATORS_DIR = ROOT / "evaluators"

# All active Python layer directories (excluding tests, archive, kb)
_ACTIVE_DIRS = [APP_DIR, QE_DIR, SIMULATORS_DIR, EVALUATORS_DIR, ROOT / "input", ROOT / "advisors"]

_FORBIDDEN_QE_ENGINE = re.compile(
    r"engine\.stat_resolution_core|engine\.runtime_consumer_registry|engine\.query_"
)
_IMPORT_RUN_STATS = re.compile(
    r"import run_stats as _h|from run_stats import|import run_stats"
)
_IMPORT_ENGINE = re.compile(r"(?:^|\n)\s*(?:from|import)\s+engine\b")
_IMPORT_PIPELINE_HELPERS = re.compile(
    r"evaluators\.pipeline_helpers|from evaluators import pipeline_helpers"
)
_IMPORT_RUN_STATS_FROM_EVALUATORS = re.compile(
    r"from run_stats import|import run_stats"
)


def _py_sources(directory: Path) -> list[Path]:
    return [p for p in directory.glob("*.py") if p.name != "__init__.py"]


def _violation_lines(src: str, pattern: re.Pattern) -> list[str]:
    return [line.strip() for line in src.splitlines() if pattern.search(line)]


# ---------------------------------------------------------------------------
# app/* boundaries
# ---------------------------------------------------------------------------

def test_app_pipeline_does_not_import_run_stats():
    """app/pipeline.py must not import root run_stats."""
    src = (APP_DIR / "pipeline.py").read_text(encoding="utf-8")
    violations = _violation_lines(src, _IMPORT_RUN_STATS)
    assert not violations, (
        f"app/pipeline.py still imports run_stats: {violations}"
    )


def test_app_files_do_not_import_run_stats():
    """No file under app/ may import root run_stats."""
    for py in _py_sources(APP_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_RUN_STATS)
        assert not violations, (
            f"{py.name} imports run_stats: {violations}"
        )


def test_app_files_do_not_import_engine():
    """No file under app/ may import engine.*."""
    for py in _py_sources(APP_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_ENGINE)
        assert not violations, (
            f"app/{py.name} imports engine: {violations}"
        )


# ---------------------------------------------------------------------------
# qe/* boundaries
# ---------------------------------------------------------------------------

def test_qe_files_do_not_import_forbidden_engine_modules():
    """No file under qe/ may import engine.stat_resolution_core, engine.query_*, or engine.runtime_consumer_registry."""
    for py in _py_sources(QE_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _FORBIDDEN_QE_ENGINE)
        assert not violations, (
            f"qe/{py.name} imports forbidden engine module: {violations}"
        )


# ---------------------------------------------------------------------------
# simulators/* boundaries
# ---------------------------------------------------------------------------

def test_simulators_files_do_not_import_engine():
    """No file under simulators/ may import engine.*."""
    for py in _py_sources(SIMULATORS_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_ENGINE)
        assert not violations, (
            f"simulators/{py.name} imports engine: {violations}"
        )

# ---------------------------------------------------------------------------
# T12: no-bridge rules
# ---------------------------------------------------------------------------

def test_no_active_file_imports_pipeline_helpers():
    """No active file may import evaluators.pipeline_helpers (bridge deleted in T12)."""
    for active_dir in _ACTIVE_DIRS:
        if not active_dir.exists():
            continue
        for py in _py_sources(active_dir):
            src = py.read_text(encoding="utf-8")
            violations = _violation_lines(src, _IMPORT_PIPELINE_HELPERS)
            assert not violations, (
                f"{py.relative_to(ROOT)} imports pipeline_helpers (bridge): {violations}"
            )


def test_evaluators_files_do_not_import_run_stats():
    """No file under evaluators/ may import run_stats directly."""
    for py in _py_sources(EVALUATORS_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_RUN_STATS_FROM_EVALUATORS)
        assert not violations, (
            f"evaluators/{py.name} imports run_stats: {violations}"
        )
