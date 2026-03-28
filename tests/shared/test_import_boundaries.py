"""
Shared import-boundary enforcement tests.

Verifies the active-spine import boundaries that define the post-tranche architecture:
  - app/* does not import root run_stats.py
  - app/* does not import engine.*
  - qe/* does not import forbidden legacy engine authority modules
  - simulators/* does not import engine.*
  - No active layer imports from: compilers, models, optimizer, parsers, registry

Gate: fast (no computation). Fails if any boundary is violated.
"""
from __future__ import annotations

import pytest


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
# Consolidated transitional-root boundary (post-T13)
_IMPORT_TRANSITIONAL_ROOTS = re.compile(
    r"^\s*(?:from|import)\s+(?:compilers|models|optimizer|parsers|registry)\b",
    re.MULTILINE,
)

_IMPORT_QE_FROM_INPUT = re.compile(r"^\s*(?:from|import)\s+qe\b", re.MULTILINE)
_IMPORT_FORBIDDEN_INPUT_FROM_QE = re.compile(
    r"^\s*(?:from|import)\s+input\.(?:runtime_state|loader|state_builder)\b",
    re.MULTILINE,
)
_IMPORT_DELETED_LEGACY_STATE_OWNERS = re.compile(
    r"^\s*(?:from|import)\s+(?:input\.(?:ids_raw|scenario_inputs|account_state_compiler)|qe\.account_state)\b",
    re.MULTILINE,
)

pytestmark = pytest.mark.live

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


# ---------------------------------------------------------------------------
# T13: consolidated transitional-root boundaries
# ---------------------------------------------------------------------------

def test_no_active_layer_imports_from_transitional_roots():
    """No active layer file may import from compilers, models, optimizer, parsers, or registry."""
    for active_dir in _ACTIVE_DIRS:
        if not active_dir.exists():
            continue
        for py in _py_sources(active_dir):
            src = py.read_text(encoding="utf-8")
            hits = _IMPORT_TRANSITIONAL_ROOTS.findall(src)
            assert not hits, (
                f"{py.relative_to(ROOT)} imports from a transitional root "
                f"(compilers/models/optimizer/parsers/registry): {hits}"
            )


def test_no_active_layer_imports_from_engine():
    """No active layer file may import from engine.* (engine is fully shimmed)."""
    _IMPORT_ENGINE_STMT = re.compile(r"^\s*(?:from|import)\s+engine\b", re.MULTILINE)
    for active_dir in _ACTIVE_DIRS:
        if not active_dir.exists():
            continue
        for py in _py_sources(active_dir):
            src = py.read_text(encoding="utf-8")
            hits = _IMPORT_ENGINE_STMT.findall(src)
            assert not hits, (
                f"{py.relative_to(ROOT)} imports from engine (transitional root): {hits}"
            )

def test_input_files_do_not_import_qe():
    """No file under input/ may import qe.*."""
    input_dir = ROOT / "input"
    for py in _py_sources(input_dir):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_QE_FROM_INPUT)
        assert not violations, f"input/{py.name} imports qe: {violations}"


def test_qe_files_do_not_import_forbidden_input_modules():
    """qe/* may not import input.runtime_state, input.loader, or input.state_builder."""
    for py in _py_sources(QE_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_FORBIDDEN_INPUT_FROM_QE)
        assert not violations, f"qe/{py.name} imports forbidden input module: {violations}"


def test_no_active_layer_imports_deleted_legacy_state_modules():
    """Active code may not import deleted state-owner modules."""
    for active_dir in _ACTIVE_DIRS:
        if not active_dir.exists():
            continue
        for py in _py_sources(active_dir):
            src = py.read_text(encoding="utf-8")
            violations = _violation_lines(src, _IMPORT_DELETED_LEGACY_STATE_OWNERS)
            assert not violations, (
                f"{py.relative_to(ROOT)} imports deleted legacy state module: {violations}"
            )
