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

import ast
import pytest


import re
import sys
from pathlib import Path
import yaml

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
# Fixed to avoid matching import statements that mention the app pipeline surface.
_IMPORT_RUN_STATS = re.compile(
    r"\bimport\s+run_stats\b|from\s+run_stats\s+import"
)
_IMPORT_ENGINE = re.compile(r"(?:^|\n)\s*(?:from|import)\s+engine\b")
_IMPORT_PIPELINE_HELPERS = re.compile(
    r"evaluators\.pipeline_helpers|from evaluators import pipeline_helpers"
)
_IMPORT_RUN_STATS_FROM_EVALUATORS = re.compile(
    r"^\s*(?:from\s+run_stats\s+import|import\s+run_stats\b)",
    re.MULTILINE,
)
_IMPORT_PRIVATE_QE_COMPILER_SYMBOLS_FROM_EVALUATORS = re.compile(
    r"^\s*from\s+qe\.stat_input_compiler\s+import\s+.*\b_[A-Za-z0-9_]+",
    re.MULTILINE,
)
_IMPORT_APP_FROM_EVALUATORS = re.compile(
    r"^\s*(?:from\s+app(?:\.[A-Za-z0-9_]+)*\s+import|import\s+app(?:\.[A-Za-z0-9_]+)*)\b",
    re.MULTILINE,
)
_IMPORT_INPUT_FROM_EVALUATORS = re.compile(
    r"^\s*(?:from\s+input(?:\.[A-Za-z0-9_]+)*\s+import|import\s+input(?:\.[A-Za-z0-9_]+)*)\b",
    re.MULTILINE,
)
_IMPORT_PRIVATE_QE_COMPILER_SYMBOLS_FROM_APP = re.compile(
    r"^\s*from\s+qe\.stat_input_compiler\s+import\s+.*\b_[A-Za-z0-9_]+",
    re.MULTILINE,
)
# Consolidated transitional-root boundary (post-T13)
_IMPORT_TRANSITIONAL_ROOTS = re.compile(
    r"^\s*(?:from|import)\s+(?:compilers|models|optimizer|parsers|registry)\b",
    re.MULTILINE,
)

_IMPORT_QE_FROM_INPUT = re.compile(r"^\s*(?:from|import)\s+qe\b", re.MULTILINE)
_IMPORT_UPWARD_LAYER_FROM_INPUT = re.compile(
    r"^\s*(?:from|import)\s+(?:simulators|evaluators|advisors|app)\b",
    re.MULTILINE,
)
_IMPORT_UPWARD_LAYER_FROM_QE = re.compile(
    r"^\s*(?:from|import)\s+(?:simulators|evaluators|advisors|app)\b",
    re.MULTILINE,
)
_IMPORT_UPWARD_LAYER_FROM_SIMULATORS = re.compile(
    r"^\s*(?:from|import)\s+(?:evaluators|advisors|app)\b",
    re.MULTILINE,
)
_IMPORT_SIMULATORS_FROM_QE = re.compile(
    r"^\s*(?:from|import)\s+simulators\b",
    re.MULTILINE,
)
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
_ALLOWED_QE_SIMULATOR_IMPORTS: set[tuple[str, str]] = set()
_IMPORT_FORBIDDEN_INPUT_FROM_QE = re.compile(
    r"^\s*(?:from|import)\s+input\.(?:runtime_state|loader|state_builder)\b",
    re.MULTILINE,
)
_IMPORT_FORBIDDEN_QE_COMPAT_FROM_SIMULATORS = re.compile(
    r"^\s*(?:from|import)\s+qe\.stat_resolution\b",
    re.MULTILINE,
)
_IMPORT_QE_STAT_RESOLUTION = re.compile(
    r"^\s*(?:from|import)\s+qe\.stat_resolution\b",
    re.MULTILINE,
)
_QE_DIRECT_MANUAL_INPUT_READ = re.compile(
    r"manual_inputs\.yaml|manual_input_path|manual_advisory_inputs.*safe_load|safe_load.*manual_advisory_inputs",
    re.MULTILINE,
)
_APP_DIRECT_KB_PATH_REFERENCE = re.compile(
    r"ROOT\s*/\s*['\"]kb['\"]|['\"]kb/(?:cards|modules|perks|ledgers)/",
    re.MULTILINE,
)
_ADVISORS_DIRECT_KB_PATH_REFERENCE = re.compile(r"['\"]kb/", re.MULTILINE)
_ADVISORS_CSV_PARSE_IMPORT = re.compile(r"^\s*import\s+csv\b|^\s*from\s+csv\s+import\b", re.MULTILINE)
_IMPORT_DELETED_LEGACY_STATE_OWNERS = re.compile(
    r"^\s*(?:from|import)\s+(?:input\.(?:ids_raw|scenario_inputs|account_state_compiler)|qe\.account_state)\b",
    re.MULTILINE,
)
_ARCHIVED_MANUAL_INPUT_PATH = re.compile(r"input/assumptions\.yaml")
_LOADER_RUNTIME_TIMELINE = re.compile(r"perk_timeline|generate_timeline|runtime_timeline")
_DIRECT_QE_RESOLVE_CALL = re.compile(r"\bresolve_stats\(")
_ACTIVE_OUTPUT_LEGACY_SURFACE_PREFIX = re.compile(
    r"\b(?:canonical_stat|runtime_mechanic_param|environment_param|account_flag|account_context|meta_progression_param|cosmetic_bonus)::"
)
_LEGACY_PREFIX_IN_ACTIVE_CODE = re.compile(
    r"(canonical_stat::|mechanic_param::|runtime_mechanic_param::|environment_param::|account_flag::|account_context::|meta_progression_param::|capability::|cosmetic_bonus::)"
)
_QE_OWNED_SYMBOL_DEFINITION = re.compile(
    r"^\s*(?:def\s+(?:resolve_stats|publish_query_surfaces)\s*\(|class\s+(?:StatQueryKernel|DependencyRegistry|FamilyBaselineMaterializer)\b)",
    re.MULTILINE,
)

_ROOT_FILE_ALLOWLIST = {
    ".gitignore",
    "ACTIVE_TRANCHE.md",
    "AGENTS.md",
    "ARCHITECTURE.md",
    "BURNDOWN.yaml",
    "CODEX_SUPERVISOR_PROMPT.txt",
    "README.md",
    "REPO_INDEX.yaml",
    "RTK.md",
    "TowerSim_bible_v49.md",
    "TowerSim_bible_v49_reconciliation_review.md",
    "pyproject.toml",
    "requirements.txt",
}
_TESTS_ROOT_FILE_ALLOWLIST = {"conftest.py"}
_INPUT_FILE_ALLOWLIST = {
    "ids_parser.py",
    "lab_category_registry.py",
    "loader.py",
    "manual_inputs.contract.yaml",
    "manual_inputs.yaml",
    "runtime_state.py",
    "state_builder.py",
    "state_types.py",
}
_APP_FILE_ALLOWLIST = {
    "__init__.py",
    "boss_waves_phase2a_field_map.yaml",
    "display.py",
    "inspector_data.py",
    "models.py",
    "pipeline.py",
    "publication.py",
    "run_analysis.py",
    "run_stats.py",
    "streamlit_inspector.py",
}
_QE_FILE_ALLOWLIST = {
    "__init__.py",
    "shared_runtime_context.py",
    "consumer_registry.py",
    "contracts.py",
    "dependency_registry.py",
    "kb_surfaces.py",
    "kernel.py",
    "materializer.py",
    "models.py",
    "perk_tables.py",
    "publication.py",
    "run_plan.py",
    "query_currency_income.py",
    "query_derived_composites.py",
    "query_module_policy.py",
    "query_perk_compiler.py",
    "query_routing.py",
    "query_state_mode_policy.py",
    "routing.py",
    "stat_input_compiler.py",
    "stat_resolution.py",
    "workshop_stat_rows.py",
}
_SIMULATORS_FILE_ALLOWLIST = {
    "__init__.py",
    "contracts.py",
    "evaluator_kernel.py",
    "incremental_cache_fingerprint.py",
    "incremental_cache_validator.py",
    "incremental_overlay_publisher.py",
    "incremental_parity_harness.py",
    "incremental_recalc_runtime.py",
    "incremental_subset_executor.py",
    "performance.py",
    "perks.py",
    "perk_timeline_generator.py",
    "perk_timeline_state.py",
    "progression.py",
    "runtime_consumer_executor.py",
    "scenario.py",
    "snapshot_resolver.py",
    "timing.py",
    "wave_progression_policy.py",
}
_EVALUATORS_FILE_ALLOWLIST = {
    "__init__.py",
    "audit_engine.py",
    "compare.py",
    "compare_core.py",
    "objectives.py",
    "ranker.py",
    "residue_analysis.py",
    "scorer.py",
    "verification_engine.py",
}

pytestmark = pytest.mark.live


def _extract_inventory_from_architecture(heading: str) -> set[str]:
    doc = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    pattern = re.compile(
        rf"### {re.escape(heading)}\n\n.*?Allowed direct files are:\n\n(.*?)(?:\n\nNo new direct files may be added under)",
        re.DOTALL,
    )
    match = pattern.search(doc)
    assert match, f"Could not find inventory section: {heading}"
    return {m.group(1) for m in re.finditer(r"- `([^`]+)`", match.group(1))}


def _active_candidate_python_files_from_repo_index(section: str) -> set[str]:
    repo_index = yaml.safe_load((ROOT / "REPO_INDEX.yaml").read_text(encoding="utf-8"))
    section_map = repo_index[section]
    names = set()
    for key, metadata in section_map.items():
        if not isinstance(metadata, dict):
            continue
        if metadata.get("status") != "active_candidate":
            continue
        if not key.endswith(".py"):
            continue
        names.add(Path(key).name)
    return names


def _repo_index_contains_key(section: str, key: str) -> bool:
    repo_index = yaml.safe_load((ROOT / "REPO_INDEX.yaml").read_text(encoding="utf-8"))
    section_map = repo_index.get(section, {})
    return key in section_map

def _py_sources(directory: Path) -> list[Path]:
    return [p for p in directory.glob("*.py") if p.name != "__init__.py"]


def _violation_lines(src: str, pattern: re.Pattern) -> list[str]:
    return [line.strip() for line in src.splitlines() if pattern.search(line)]


def _violation_line_details(src: str, pattern: re.Pattern) -> list[str]:
    return [
        f"L{lineno}: {line.strip()}"
        for lineno, line in enumerate(src.splitlines(), start=1)
        if pattern.search(line)
    ]


def _boundary_violation_details(directory: Path, pattern: re.Pattern) -> list[str]:
    details: list[str] = []
    for py in _py_sources(directory):
        src = py.read_text(encoding="utf-8")
        violating_lines = _violation_line_details(src, pattern)
        if violating_lines:
            details.append(f"{py.relative_to(ROOT)} -> {violating_lines}")
    return details


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


def test_app_files_do_not_import_private_qe_stat_input_compiler_symbols():
    """App layer must use public qe.stat_input_compiler surfaces only."""
    for py in _py_sources(APP_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_PRIVATE_QE_COMPILER_SYMBOLS_FROM_APP)
        assert not violations, (
            f"app/{py.name} imports private qe.stat_input_compiler symbols: {violations}"
        )


def test_app_files_do_not_reference_kb_paths_directly():
    """App layer must not own direct kb/* path references for reference data or ledgers."""
    for py in _py_sources(APP_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _APP_DIRECT_KB_PATH_REFERENCE)
        assert not violations, f"app/{py.name} references kb paths directly: {violations}"


def test_app_publication_delegates_dashboard_assembly_to_qe():
    """app/publication.py should stay a thin wrapper around QE-owned dashboard builders."""
    src = (APP_DIR / "publication.py").read_text(encoding="utf-8")
    forbidden_defs = [
        "def _build_workshop_panel(",
        "def _build_uw_panel(",
        "def _stats_rows_by_surface(",
        "def _rows_with_qe_derived_values(",
    ]
    for marker in forbidden_defs:
        assert marker not in src, f"app/publication.py still defines dashboard assembly helper {marker}"
    required_delegations = [
        "qe_build_input_dashboard_payload(",
        "qe_build_stats_dashboard_payload(",
        "qe_build_labs_panel(",
    ]
    for marker in required_delegations:
        assert marker in src, f"app/publication.py should delegate through {marker}"


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


def test_simulators_do_not_import_qe_stat_resolution_directly():
    """Simulator code must not depend directly on the compat/report resolver module."""
    for py in _py_sources(SIMULATORS_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_FORBIDDEN_QE_COMPAT_FROM_SIMULATORS)
        assert not violations, (
            f"simulators/{py.name} imports qe.stat_resolution directly: {violations}"
        )


def test_only_qe_routing_may_import_qe_stat_resolution():
    """qe.stat_resolution is an internal QE boundary; active non-QE files must not import it directly."""
    allowed = {ROOT / "qe" / "routing.py", ROOT / "qe" / "kernel.py"}
    for active_dir in _ACTIVE_DIRS:
        if not active_dir.exists():
            continue
        for py in _py_sources(active_dir):
            src = py.read_text(encoding="utf-8")
            violations = _violation_lines(src, _IMPORT_QE_STAT_RESOLUTION)
            if not violations:
                continue
            assert py in allowed, (
                f"{py.relative_to(ROOT)} imports qe.stat_resolution directly: {violations}"
            )


def test_qe_routing_only_imports_allowed_stat_resolution_symbols():
    """routing.py may touch qe.stat_resolution only for the explicit report fallback."""
    path = ROOT / "qe" / "routing.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    allowed_names = {
        "resolve_stats",
        "resolve_stats_delta",
    }
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "qe.stat_resolution":
            continue
        imported_names.update(alias.name for alias in node.names)
    assert imported_names == allowed_names, (
        "qe/routing.py should import only the explicit report fallback from "
        f"qe.stat_resolution, found {sorted(imported_names)!r}"
    )


def test_qe_routing_calls_report_fallback_only_in_hybrid_report_builders():
    """The qe.stat_resolution fallback may only be invoked from explicit hybrid/report builders."""
    path = ROOT / "qe" / "routing.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    parent_stack: list[ast.AST] = []
    fallback_call_parents: list[str] = []

    class _Visitor(ast.NodeVisitor):
        def generic_visit(self, node):
            parent_stack.append(node)
            super().generic_visit(node)
            parent_stack.pop()

        def visit_Call(self, node: ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "_fallback_resolve_stats":
                for parent in reversed(parent_stack):
                    if isinstance(parent, ast.FunctionDef):
                        fallback_call_parents.append(parent.name)
                        break
                else:
                    fallback_call_parents.append("<module>")
            self.generic_visit(node)

    _Visitor().visit(tree)
    assert sorted(fallback_call_parents) == [
        "_resolve_hybrid_statbook_from_bound_inputs",
        "_resolve_hybrid_statbook_from_rows",
    ], (
        "The report fallback should only be called from the explicit hybrid/report builders, "
        f"found {sorted(fallback_call_parents)!r}"
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


def test_evaluators_do_not_import_private_qe_compiler_symbols():
    """Evaluator layer must consume public qe.stat_input_compiler surfaces only."""
    for py in _py_sources(EVALUATORS_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_PRIVATE_QE_COMPILER_SYMBOLS_FROM_EVALUATORS)
        assert not violations, (
            f"evaluators/{py.name} imports private qe.stat_input_compiler symbols: {violations}"
        )


def test_evaluators_files_do_not_import_app_layer():
    """No file under evaluators/ may import app.* surfaces."""
    for py in _py_sources(EVALUATORS_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_APP_FROM_EVALUATORS)
        assert not violations, (
            f"evaluators/{py.name} imports app layer symbols: {violations}"
        )


def test_evaluators_files_do_not_import_input_layer():
    """No file under evaluators/ may import input.* surfaces beyond the explicit compat allowlist."""
    for py in _py_sources(EVALUATORS_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_INPUT_FROM_EVALUATORS)
        unexpected = [
            line for line in violations
            if (py.name, line) not in _ALLOWED_EVALUATOR_INPUT_IMPORTS
        ]
        assert not unexpected, (
            f"evaluators/{py.name} imports unexpected input layer symbols: {unexpected}"
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


def test_input_files_do_not_import_upward_layers():
    """No file under input/ may import simulators, evaluators, advisors, or app."""
    input_dir = ROOT / "input"
    for py in _py_sources(input_dir):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_UPWARD_LAYER_FROM_INPUT)
        assert not violations, f"input/{py.name} imports an upward layer: {violations}"


def test_qe_files_do_not_import_upward_layers():
    """No file under qe/ may import upward layers except explicit compat seams."""
    violations: list[str] = []
    for py in _py_sources(QE_DIR):
        src = py.read_text(encoding="utf-8")
        for line in _violation_lines(src, _IMPORT_UPWARD_LAYER_FROM_QE):
            if (py.name, line) in _ALLOWED_QE_SIMULATOR_IMPORTS:
                continue
            violations.append(f"{py.relative_to(ROOT)} -> {line}")
    assert not violations, (
        "Upward-layer imports detected in qe/*.py (forbidden: simulators/evaluators/advisors/app): "
        f"{violations}"
    )


def test_qe_files_do_not_import_simulators():
    """No file under qe/ may import simulators.* beyond the explicit compat allowlist."""
    violations: list[str] = []
    for py in _py_sources(QE_DIR):
        src = py.read_text(encoding="utf-8")
        for line in _violation_lines(src, _IMPORT_SIMULATORS_FROM_QE):
            if (py.name, line) in _ALLOWED_QE_SIMULATOR_IMPORTS:
                continue
            violations.append(f"{py.relative_to(ROOT)} -> {line}")
    assert not violations, (
        "QE imports simulator layer modules directly (forbidden): "
        f"{violations}"
    )


def test_simulators_files_do_not_import_upward_layers():
    """No file under simulators/ may import evaluators, advisors, or app."""
    violations = _boundary_violation_details(SIMULATORS_DIR, _IMPORT_UPWARD_LAYER_FROM_SIMULATORS)
    assert not violations, (
        "Upward-layer imports detected in simulators/*.py (forbidden: evaluators/advisors/app): "
        f"{violations}"
    )


def test_advisors_do_not_import_or_read_kb_qe_simulators_or_input():
    """Advisor policy must consume evaluator outputs only, not lower-layer imports/file reads."""
    advisors_dir = ROOT / "advisors"
    for py in _py_sources(advisors_dir):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_OR_READ_FORBIDDEN_FROM_ADVISORS)
        assert not violations, (
            f"advisors/{py.name} imports/reads forbidden lower layers (kb/qe/simulators/input): {violations}"
        )


def test_app_files_do_not_define_non_orchestration_ownership_symbols():
    """App layer should stay orchestration/render-only; reject domain-owner symbol definitions."""
    for py in _py_sources(APP_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_line_details(src, _APP_NON_ORCHESTRATION_OWNERSHIP_MARKERS)
        assert not violations, (
            f"app/{py.name} defines non-orchestration ownership markers: {violations}"
        )


def test_qe_files_do_not_import_forbidden_input_modules():
    """qe/* may not import input.runtime_state, input.loader, or input.state_builder."""
    for py in _py_sources(QE_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _IMPORT_FORBIDDEN_INPUT_FROM_QE)
        assert not violations, f"qe/{py.name} imports forbidden input module: {violations}"


def test_qe_files_do_not_read_manual_inputs_directly():
    """qe/* must consume input-owned manual advisory data, not read manual input files directly."""
    for py in _py_sources(QE_DIR):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _QE_DIRECT_MANUAL_INPUT_READ)
        assert not violations, f"qe/{py.name} reads manual inputs directly: {violations}"

def test_advisors_files_do_not_reference_kb_paths_directly():
    """advisors/* must consume evaluator bundles, not own kb/* file path references."""
    advisor_dir = ROOT / "advisors"
    for py in _py_sources(advisor_dir):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _ADVISORS_DIRECT_KB_PATH_REFERENCE)
        assert not violations, f"advisors/{py.name} references kb/ path directly: {violations}"


def test_advisors_files_do_not_parse_csv_directly():
    """advisors/* should not parse CSV directly; evaluator layer owns advisory input materialisation."""
    advisor_dir = ROOT / "advisors"
    for py in _py_sources(advisor_dir):
        src = py.read_text(encoding="utf-8")
        violations = _violation_lines(src, _ADVISORS_CSV_PARSE_IMPORT)
        assert not violations, f"advisors/{py.name} imports csv directly: {violations}"


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


def test_active_layers_do_not_reference_archived_manual_input_path():
    """Active layer files should reference the canonical manual_inputs.yaml path only."""
    for active_dir in _ACTIVE_DIRS:
        if not active_dir.exists():
            continue
        for py in _py_sources(active_dir):
            src = py.read_text(encoding="utf-8")
            violations = _violation_lines(src, _ARCHIVED_MANUAL_INPUT_PATH)
            assert not violations, (
                f"{py.relative_to(ROOT)} references archived manual input path: {violations}"
            )


def test_input_loader_does_not_regress_to_runtime_timeline_generation():
    """input/loader.py must stay free of simulator-owned runtime timeline generation."""
    src = (ROOT / "input" / "loader.py").read_text(encoding="utf-8")
    violations = _violation_lines(src, _LOADER_RUNTIME_TIMELINE)
    assert not violations, f"input/loader.py regressed to runtime timeline generation: {violations}"


def test_repo_layout_allowlists_remain_explicit():
    """Keep root and tests/ root direct-file sprawl under an explicit allowlist."""
    # Exclude .git — in a git worktree it is a plain file (gitdir pointer), not a directory
    root_files = {p.name for p in ROOT.iterdir() if p.is_file() and p.name != '.git'}
    tests_root_files = {p.name for p in (ROOT / "tests").iterdir() if p.is_file()}
    assert root_files <= _ROOT_FILE_ALLOWLIST, f"Unexpected repo-root files: {sorted(root_files - _ROOT_FILE_ALLOWLIST)}"
    assert tests_root_files <= _TESTS_ROOT_FILE_ALLOWLIST, (
        f"Unexpected tests/ root files: {sorted(tests_root_files - _TESTS_ROOT_FILE_ALLOWLIST)}"
    )


def test_input_direct_file_inventory_remains_explicit():
    """Keep input/ root-file sprawl under an explicit architecture-approved allowlist."""
    input_dir = ROOT / "input"
    input_files = {p.name for p in input_dir.iterdir() if p.is_file()}
    assert input_files <= _INPUT_FILE_ALLOWLIST, (
        f"Unexpected input/ files: {sorted(input_files - _INPUT_FILE_ALLOWLIST)}"
    )


def test_app_direct_file_inventory_remains_explicit():
    """Keep app/ root-file sprawl under an explicit architecture-approved allowlist."""
    app_files = {p.name for p in APP_DIR.iterdir() if p.is_file()}
    assert app_files <= _APP_FILE_ALLOWLIST, (
        f"Unexpected app/ files: {sorted(app_files - _APP_FILE_ALLOWLIST)}"
    )


def test_qe_direct_file_inventory_remains_explicit():
    """Keep qe/ root-file sprawl under an explicit architecture-approved allowlist."""
    qe_files = {p.name for p in QE_DIR.iterdir() if p.is_file()}
    assert qe_files <= _QE_FILE_ALLOWLIST, (
        f"Unexpected qe/ files: {sorted(qe_files - _QE_FILE_ALLOWLIST)}"
    )


def test_simulators_direct_file_inventory_remains_explicit():
    """Keep simulators/ root-file sprawl under an explicit architecture-approved allowlist."""
    simulator_files = {p.name for p in SIMULATORS_DIR.iterdir() if p.is_file()}
    assert simulator_files <= _SIMULATORS_FILE_ALLOWLIST, (
        f"Unexpected simulators/ files: {sorted(simulator_files - _SIMULATORS_FILE_ALLOWLIST)}"
    )


def test_evaluators_direct_file_inventory_remains_explicit():
    """Keep evaluators/ root-file sprawl under an explicit architecture-approved allowlist."""
    evaluators_files = {p.name for p in EVALUATORS_DIR.iterdir() if p.is_file()}
    assert evaluators_files <= _EVALUATORS_FILE_ALLOWLIST, (
        f"Unexpected evaluators/ files: {sorted(evaluators_files - _EVALUATORS_FILE_ALLOWLIST)}"
    )


def test_architecture_inventory_matches_repo_index_for_app_and_simulators():
    """
    Governance consistency guard:
    ARCHITECTURE.md inventory, REPO_INDEX active candidates, and boundary-test allowlists
    must stay aligned for app/ and simulators/.
    """
    app_inventory = _extract_inventory_from_architecture("App inventory control")
    simulators_inventory = _extract_inventory_from_architecture("Simulator inventory control")

    assert app_inventory == _APP_FILE_ALLOWLIST, (
        "ARCHITECTURE.md app inventory does not match test allowlist: "
        f"{sorted(app_inventory ^ _APP_FILE_ALLOWLIST)}"
    )
    assert simulators_inventory == _SIMULATORS_FILE_ALLOWLIST, (
        "ARCHITECTURE.md simulators inventory does not match test allowlist: "
        f"{sorted(simulators_inventory ^ _SIMULATORS_FILE_ALLOWLIST)}"
    )

    app_repo_index = _active_candidate_python_files_from_repo_index("app")
    simulators_repo_index = _active_candidate_python_files_from_repo_index("simulators")
    app_python_allowlist = {name for name in _APP_FILE_ALLOWLIST if name.endswith(".py")}
    assert app_repo_index == app_python_allowlist, (
        "REPO_INDEX.yaml app active candidates do not match test allowlist: "
        f"{sorted(app_repo_index ^ app_python_allowlist)}"
    )
    assert simulators_repo_index == _SIMULATORS_FILE_ALLOWLIST, (
        "REPO_INDEX.yaml simulators active candidates do not match test allowlist: "
        f"{sorted(simulators_repo_index ^ _SIMULATORS_FILE_ALLOWLIST)}"
    )


def test_governance_docs_do_not_reference_absent_legacy_runtime_paths():
    """Governance docs should not describe legacy runtime files/directories that are absent on this branch."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "python run_stats.py" not in readme, "README.md still instructs using missing root run_stats.py"
    assert "`run_stats.py` — legacy domain helper library" not in readme, (
        "README.md still lists missing root run_stats.py as a key active file"
    )
    assert "`engine/` shims re-export from active layers" not in readme, (
        "README.md still claims engine shims exist on this branch"
    )
    assert "`models/` shims re-export from `qe.models`." not in readme, (
        "README.md still claims models shims exist on this branch"
    )

    assert not (ROOT / "run_stats.py").exists(), "Unexpected root run_stats.py present; update governance checks."
    assert not _repo_index_contains_key("root", "run_stats.py"), (
        "REPO_INDEX.yaml root section still tracks missing run_stats.py entry"
    )
    assert not (ROOT / "simulators" / "run_executor.py").exists(), (
        "Unexpected simulators/run_executor.py present; legacy executor retirement must update governance checks."
    )
    assert not _repo_index_contains_key("simulators", "simulators/run_executor.py"), (
        "REPO_INDEX.yaml simulators section still tracks deleted simulators/run_executor.py entry"
    )

    for stale_section in ("archive", "engine_shims", "models_shims"):
        assert stale_section not in yaml.safe_load((ROOT / "REPO_INDEX.yaml").read_text(encoding="utf-8")), (
            f"REPO_INDEX.yaml still includes stale '{stale_section}' section for absent paths."
        )


def test_app_and_compare_use_qe_planner_not_direct_resolve_calls():
    """App pipeline and compare builder should consume the QE planner's explicit report path, not raw resolve_stats or the ambiguous snapshot alias."""
    targets = [
        ROOT / "app" / "pipeline.py",
        ROOT / "evaluators" / "compare_core.py",
    ]
    for path in targets:
        src = path.read_text(encoding="utf-8")
        assert "QEResolutionPlanner" in src, f"{path.relative_to(ROOT)} is missing the native QE planner interface."
        assert "resolve_report_snapshot(" in src, (
            f"{path.relative_to(ROOT)} should use the planner's explicit report snapshot path."
        )
        assert "resolve_snapshot(" not in src, (
            f"{path.relative_to(ROOT)} should not use the ambiguous resolve_snapshot alias on the active path."
        )
        violations = _violation_lines(src, _DIRECT_QE_RESOLVE_CALL)
        assert not violations, f"{path.relative_to(ROOT)} still calls resolve_stats directly: {violations}"


def test_only_app_pipeline_and_compare_use_report_snapshot():
    """The explicit report snapshot path belongs only to report/orchestration consumers."""
    allowed = {
        ROOT / "app" / "pipeline.py",
        ROOT / "evaluators" / "compare.py",
        ROOT / "evaluators" / "compare_core.py",
        ROOT / "qe" / "routing.py",
    }
    for active_dir in _ACTIVE_DIRS:
        if not active_dir.exists():
            continue
        for py in _py_sources(active_dir):
            src = py.read_text(encoding="utf-8")
            if "resolve_report_snapshot(" not in src:
                continue
            assert py in allowed, (
                f"{py.relative_to(ROOT)} uses resolve_report_snapshot outside the report/orchestration boundary."
            )


def test_qe_owns_query_resolution_contract_routing_materialization_registry_and_surface_publication_symbols():
    """
    Deterministic stat/query resolution, value contracts, routing, materialisation,
    dependency registry, and sanctioned-surface publication symbols must be defined in qe only.
    """
    qe_dir = ROOT / "qe"
    for active_dir in _ACTIVE_DIRS:
        if not active_dir.exists() or active_dir == qe_dir:
            continue
        for py in _py_sources(active_dir):
            src = py.read_text(encoding="utf-8")
            hits = _QE_OWNED_SYMBOL_DEFINITION.findall(src)
            assert not hits, (
                f"{py.relative_to(ROOT)} defines QE-owned symbol(s): {hits}. "
                "Keep deterministic stat/query resolution, routing/materialisation, "
                "dependency registry, and sanctioned publication definitions in qe/* only."
            )


def test_simulator_family_queries_default_to_qe_planner():
    """Default bounded simulator family-query paths should lean on the shared QE planner interface."""
    progression_src = (ROOT / "simulators" / "progression.py").read_text(encoding="utf-8")
    timing_src = (ROOT / "simulators" / "timing.py").read_text(encoding="utf-8")

    assert "QEResolutionPlanner" in progression_src, "simulators/progression.py is missing the shared QE planner interface."
    assert "resolve_declared_family_query" in progression_src, (
        "simulators/progression.py should use planner-backed declared-family queries on its default path."
    )
    assert "resolve_report_snapshot(" not in progression_src, (
        "simulators/progression.py must not use the report snapshot path on simulator-facing execution."
    )
    assert "resolve_snapshot(" not in progression_src, (
        "simulators/progression.py must not use the ambiguous snapshot alias on simulator-facing execution."
    )
    assert "QEResolutionPlanner" in timing_src, "simulators/timing.py is missing the shared QE planner interface."
    assert "resolve_rows_declared_family_query" in timing_src, (
        "simulators/timing.py should use planner-backed rows-family queries on its default path."
    )
    assert "resolve_report_snapshot(" not in timing_src, (
        "simulators/timing.py must not use the report snapshot path on simulator-facing execution."
    )
    assert "resolve_snapshot(" not in timing_src, (
        "simulators/timing.py must not use the ambiguous snapshot alias on simulator-facing execution."
    )


def test_simulator_snapshot_resolver_stays_on_lightweight_checkpoint_path():
    """snapshot_resolver.py is a hot-path seam and must not drift back to bridge, compat, or app orchestration imports."""
    path = ROOT / "simulators" / "snapshot_resolver.py"
    src = path.read_text(encoding="utf-8")

    assert "resolve_checkpoint_surfaces" in src, (
        "simulators/snapshot_resolver.py must keep using the explicit QE checkpoint seam."
    )
    assert "ProgressionRecalcBridge" not in src, (
        "simulators/snapshot_resolver.py must not depend on ProgressionRecalcBridge."
    )
    assert "qe.stat_resolution" not in src, (
        "simulators/snapshot_resolver.py must not import qe.stat_resolution."
    )
    assert "app.pipeline" not in src, (
        "simulators/snapshot_resolver.py must not depend on app.pipeline orchestration."
    )
    assert "resolve_report_snapshot(" not in src, (
        "simulators/snapshot_resolver.py must not use the report snapshot path."
    )
    assert "resolve_stats(" not in src, (
        "simulators/snapshot_resolver.py must not call the broad compat/report resolver."
    )


def test_boss_waves_replacement_kernel_stays_off_legacy_runtime_paths():
    """The staged Boss Waves kernel must not become a wrapper around legacy runtime engines."""
    for path in (ROOT / "qe" / "run_plan.py", ROOT / "simulators" / "evaluator_kernel.py"):
        src = path.read_text(encoding="utf-8")
        forbidden = (
            "simulators.run_executor",
            "simulators.snapshot_resolver",
            "simulators.runtime_consumer_executor",
            "simulators.incremental_",
            "app.",
        )
        hits = [token for token in forbidden if token in src]
        assert not hits, f"{path.relative_to(ROOT)} imports or references forbidden Boss Waves runtime path(s): {hits}"

    qe_plan_src = (ROOT / "qe" / "run_plan.py").read_text(encoding="utf-8")
    assert "from simulators" not in qe_plan_src and "import simulators" not in qe_plan_src, (
        "qe/run_plan.py must stay below simulators and own only the common trajectory table."
    )
    evaluator_src = (ROOT / "simulators" / "evaluator_kernel.py").read_text(encoding="utf-8")
    assert "tower_damage_per_second" not in evaluator_src, (
        "simulators/evaluator_kernel.py must use v21 event-only boss TTK, not continuous DPS proxy logic."
    )


def test_active_generated_outputs_do_not_publish_legacy_surface_prefixes():
    """Committed active JSON artifacts under out/ must publish contract names, not legacy prefixes."""
    import subprocess
    expected_tracked = {
        ROOT / "out" / "account_state.json",
        ROOT / "out" / "boss_wave_milestone_matrix.json",
        ROOT / "out" / "run_stats.json",
        ROOT / "out" / "run_stats_query_plan_start_of_run.json",
        ROOT / "out" / "run_stats_query_plan_max_progression.json",
        ROOT / "out" / "run_stats_query_rows_start_of_run.json",
        ROOT / "out" / "run_stats_query_rows_max_progression.json",
    }
    output_dir = ROOT / "out"
    if not output_dir.exists():
        return
    # Only check files that are tracked by git; out/ may be gitignored.
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(output_dir)],
            cwd=ROOT, capture_output=True,
        )
        if result.returncode != 0:
            return  # out/ is not tracked; nothing to enforce
        tracked = {
            ROOT / line for line in
            subprocess.check_output(["git", "ls-files", str(output_dir)], cwd=ROOT)
            .decode().splitlines()
        }
    except Exception:
        return
    assert tracked == expected_tracked, (
        "Tracked out/ artifacts must stay equal to the sanctioned committed bounded run_stats baseline."
    )
    for path in sorted(output_dir.glob("*.json")):
        if path not in tracked:
            continue
        text = path.read_text(encoding="utf-8")
        violations = _ACTIVE_OUTPUT_LEGACY_SURFACE_PREFIX.findall(text)
        assert not violations, f"{path.relative_to(ROOT)} still publishes legacy surface prefixes: {sorted(set(violations))}"


def test_compare_and_qe_derived_only_use_legacy_prefixes_in_normalization_helpers():
    """Legacy surface prefixes may only appear inside the dedicated normalization helper shims."""
    allowed_lines = {
        "COMPAT_LEGACY_RUNTIME_ONLY_PREFIXES,",
    }
    targets = [
        ROOT / "evaluators" / "compare.py",
        ROOT / "qe" / "query_derived_composites.py",
    ]
    for path in targets:
        src = path.read_text(encoding="utf-8")
        violations = [
            line.strip()
            for line in src.splitlines()
            if _LEGACY_PREFIX_IN_ACTIVE_CODE.search(line) and line.strip() not in allowed_lines
        ]
        assert not violations, f"{path.relative_to(ROOT)} still contains active legacy surface literals: {violations[:10]}"


def test_qe_internal_naming_files_only_use_legacy_prefixes_in_normalization_helpers():
    """QE internal naming-heavy modules may only mention legacy prefixes inside normalization helper lines."""
    allowed_lines = {
        "compat_surface_from_legacy_canonical('free_upgrade_multiplier'): 'support_surface::free_upgrade_multiplier',",
        "compat_surface_from_legacy_mechanic('module.galaxy_compressor.uw_cooldown_reduction_seconds'): 'support_surface::timing.gcomp_cooldown_reduction_seconds',",
        "'support_surface::free_upgrade_multiplier': 'state::tower.free_upgrade_multiplier',",
        "'support_surface::timing.gcomp_cooldown_reduction_seconds': 'state::module.galaxy_compressor.uw_cooldown_reduction_seconds',",
        "'canonical_stat::free_upgrade_multiplier': 'support_surface::free_upgrade_multiplier',",
    }
    targets = [
        ROOT / "qe" / "routing.py",
        ROOT / "qe" / "materializer.py",
        ROOT / "qe" / "publication.py",
    ]
    for path in targets:
        violations = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if _LEGACY_PREFIX_IN_ACTIVE_CODE.search(line):
                if path.name == "materializer.py" and stripped in allowed_lines:
                    continue
                if path.name == "routing.py" and "legacy runtime_mechanic_param:: prefix" in stripped:
                    continue
                if path.name == "incremental_subset_executor.py" and (
                    "'support_surface::free_upgrade_multiplier': 'canonical_stat::free_upgrade_multiplier'," in stripped
                ):
                    continue
                violations.append(stripped)
        assert not violations, f"{path.relative_to(ROOT)} still contains active legacy surface literals: {violations[:10]}"


def test_simulator_naming_files_only_use_legacy_prefixes_in_normalization_helpers():
    """Simulator naming-heavy modules may only mention legacy prefixes inside normalization helper lines."""
    targets = [
        ROOT / "simulators" / "scenario.py",
        ROOT / "simulators" / "timing.py",
        ROOT / "simulators" / "incremental_subset_executor.py",
    ]
    for path in targets:
        violations = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if _LEGACY_PREFIX_IN_ACTIVE_CODE.search(line):
                if path.name == "scenario.py" and (
                    stripped == "return normalize_surface_id_to_contract(f'mechanic_param::{destination_id}')" or
                    "canonical_stat::" in stripped or
                    "runtime_mechanic_param::" in stripped or
                    "environment_param::" in stripped
                ):
                    continue
                if path.name == "timing.py" and stripped in {
                    "return normalize_surface_id_to_contract(f'mechanic_param::{destination_id}')",
                    "return normalize_surface_id_to_contract(f'runtime_mechanic_param::{destination_id}')",
                }:
                    continue
                if path.name == "incremental_subset_executor.py" and (
                    "'support_surface::free_upgrade_multiplier': 'canonical_stat::free_upgrade_multiplier'," in stripped
                ):
                    continue
                violations.append(stripped)
        assert not violations, f"{path.relative_to(ROOT)} still contains active legacy surface literals: {violations[:10]}"


def test_qe_stat_resolution_only_uses_legacy_prefixes_in_normalization_helpers():
    """Fallback stat-resolution shim may only mention legacy prefixes in its normalization helper definitions."""
    path = ROOT / "qe" / "stat_resolution.py"
    allowed_patterns = [
        r"'canonical_stat::tower_hp': \('canonical_stat::wall_hp',\),",
        r"'canonical_stat::tower_regen': \('canonical_stat::wall_regen',\),",
        r"'canonical_stat::",
        r"return normalize_surface_id_to_contract\(f'canonical_stat::{destination_id}'\)",
    ]
    violations = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if _LEGACY_PREFIX_IN_ACTIVE_CODE.search(line):
            if any(re.search(pattern, stripped) for pattern in allowed_patterns):
                continue
            violations.append(stripped)
    assert not violations, f"{path.relative_to(ROOT)} still contains active legacy surface literals: {violations[:10]}"
