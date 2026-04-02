"""
Architecture-governance tests for strict layer-consumption contracts.

These checks are intentionally independent from output-correctness tests; they
validate ownership/consumption boundaries directly from source imports and
governance docs.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "app"
QE_DIR = ROOT / "qe"
EVALUATORS_DIR = ROOT / "evaluators"
ADVISORS_DIR = ROOT / "advisors"

pytestmark = pytest.mark.live

_EXPECTED_RULE_LINES = (
    "- `input/` owns parsing/state assembly only.",
    "- `kb/` owns mechanic truth only.",
    "- `qe/` owns deterministic stat resolution.",
    "- `simulators/` consume QE only.",
    "- `evaluators/` consume simulator/QE outputs only.",
    "- `advisors/` consume evaluator outputs only.",
    "- `app/` orchestrates/renders only.",
    "- `tests/` enforce architecture truth.",
)

_IMPORT_INPUT_FROM_EVALUATORS = re.compile(
    r"^\s*(?:from\s+input(?:\.[A-Za-z0-9_]+)*\s+import|import\s+input(?:\.[A-Za-z0-9_]+)*)\b",
    re.MULTILINE,
)
_IMPORT_SIMULATORS_FROM_QE = re.compile(r"^\s*(?:from|import)\s+simulators\b", re.MULTILINE)
_IMPORT_OR_READ_FORBIDDEN_FROM_ADVISORS = re.compile(
    r"^\s*(?:from|import)\s+(?:kb|qe|simulators|input)\b|['\"](?:kb|qe|simulators|input)/",
    re.MULTILINE,
)
_APP_NON_ORCHESTRATION_OWNERSHIP_MARKERS = re.compile(
    r"^\s*(?:def|class)\s+("
    r"StatQueryKernel|DependencyRegistry|FamilyBaselineMaterializer|"
    r"compute_(?:ehp|edamage|eecon)|"
    r"(?:build_)?(?:recommendation|advisor|scor(?:e|er)|objective|ranker|simulate|materialize|resolve_stats)"
    r")\b",
    re.MULTILINE,
)
_ALLOWED_EVALUATOR_INPUT_IMPORTS = {
    ("compare.py", "from input.runtime_state import build_runtime_state"),
    ("compare.py", "from input.state_types import PerkSelection"),
    ("compare_core.py", "from input.runtime_state import build_runtime_state"),
    ("audit_engine.py", "from input.state_types import PerkSelection"),
    ("audit_engine.py", "from input.runtime_state import build_runtime_state"),
}
_ALLOWED_QE_SIMULATOR_IMPORTS = {
    ("routing.py", "from simulators.incremental_recalc_runtime import IncrementalRecalcRuntime"),
}


def _py_sources(directory: Path) -> list[Path]:
    return [p for p in directory.glob("*.py") if p.name != "__init__.py"]


def _matches(src: str, pattern: re.Pattern[str]) -> list[str]:
    return [line.strip() for line in src.splitlines() if pattern.search(line)]


def test_governance_docs_define_strict_layer_consumption_rules():
    arch_text = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    for line in _EXPECTED_RULE_LINES:
        assert line in arch_text, f"ARCHITECTURE.md missing strict rule line: {line}"
        assert line in readme_text, f"README.md missing strict rule line: {line}"


def test_evaluators_do_not_import_input():
    violations: list[str] = []
    for py in _py_sources(EVALUATORS_DIR):
        hits = _matches(py.read_text(encoding="utf-8"), _IMPORT_INPUT_FROM_EVALUATORS)
        unexpected = [line for line in hits if (py.name, line) not in _ALLOWED_EVALUATOR_INPUT_IMPORTS]
        if unexpected:
            violations.append(f"{py.relative_to(ROOT)} -> {unexpected}")
    assert not violations, f"Evaluators must not import input.*: {violations}"


def test_advisors_do_not_import_or_read_lower_layers():
    violations: list[str] = []
    for py in _py_sources(ADVISORS_DIR):
        hits = _matches(py.read_text(encoding="utf-8"), _IMPORT_OR_READ_FORBIDDEN_FROM_ADVISORS)
        if hits:
            violations.append(f"{py.relative_to(ROOT)} -> {hits}")
    assert not violations, f"Advisors must not import/read kb/qe/simulators/input directly: {violations}"


def test_qe_does_not_import_simulators():
    violations: list[str] = []
    for py in _py_sources(QE_DIR):
        hits = _matches(py.read_text(encoding="utf-8"), _IMPORT_SIMULATORS_FROM_QE)
        unexpected = [line for line in hits if (py.name, line) not in _ALLOWED_QE_SIMULATOR_IMPORTS]
        if unexpected:
            violations.append(f"{py.relative_to(ROOT)} -> {unexpected}")
    assert not violations, f"QE must not import simulators.*: {violations}"


def test_app_has_no_non_orchestration_owner_markers():
    violations: list[str] = []
    for py in _py_sources(APP_DIR):
        hits = _matches(py.read_text(encoding="utf-8"), _APP_NON_ORCHESTRATION_OWNERSHIP_MARKERS)
        if hits:
            violations.append(f"{py.relative_to(ROOT)} -> {hits}")
    assert not violations, f"App must stay orchestration/render-only: {violations}"
