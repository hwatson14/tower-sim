from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALLOWLIST_PATH = REPO_ROOT / "audit" / "stat_pipeline_guardrails_allowlist.yaml"


@dataclass(frozen=True)
class GuardrailViolation:
    function_name: str
    file_path: str


def _iter_python_files(scan_roots: Iterable[str]) -> Iterable[Path]:
    for root in scan_roots:
        root_path = REPO_ROOT / root
        if not root_path.exists():
            continue
        for path in root_path.rglob("*.py"):
            yield path


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def discover_function_calls(
    *,
    function_names: Set[str],
    scan_roots: Iterable[str],
) -> Dict[str, Set[str]]:
    discovered: Dict[str, Set[str]] = {name: set() for name in function_names}
    for py_path in _iter_python_files(scan_roots):
        relative = py_path.relative_to(REPO_ROOT).as_posix()
        source = py_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=relative)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            call_name = _call_name(node)
            if call_name in function_names:
                discovered[call_name].add(relative)
    return discovered


def load_allowlist(path: Path = DEFAULT_ALLOWLIST_PATH) -> Tuple[Dict[str, Set[str]], List[str]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    functions_raw = raw.get("functions", {})
    if not isinstance(functions_raw, dict):
        raise ValueError("Allowlist 'functions' must be a mapping.")
    functions: Dict[str, Set[str]] = {}
    for key, values in functions_raw.items():
        if not isinstance(values, list):
            raise ValueError(f"Allowlist entry for {key!r} must be a list.")
        functions[str(key)] = {str(item) for item in values}

    scan_roots_raw = raw.get("scan_roots", ["tower_sim", "scripts"])
    if not isinstance(scan_roots_raw, list):
        raise ValueError("Allowlist 'scan_roots' must be a list.")
    scan_roots = [str(item) for item in scan_roots_raw]
    return functions, scan_roots


def validate_guardrails(path: Path = DEFAULT_ALLOWLIST_PATH) -> List[GuardrailViolation]:
    allowed_map, scan_roots = load_allowlist(path)
    discovered = discover_function_calls(
        function_names=set(allowed_map.keys()),
        scan_roots=scan_roots,
    )
    violations: List[GuardrailViolation] = []
    for function_name, seen_files in discovered.items():
        allowed_files = allowed_map.get(function_name, set())
        for file_path in sorted(seen_files - allowed_files):
            violations.append(
                GuardrailViolation(function_name=function_name, file_path=file_path)
            )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Stat pipeline guardrail: fail if new runtime bypass callsites are introduced."
        )
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=DEFAULT_ALLOWLIST_PATH,
        help="Path to guardrail allowlist YAML.",
    )
    args = parser.parse_args()

    violations = validate_guardrails(args.allowlist)
    if violations:
        for violation in violations:
            print(
                f"guardrail_violation:{violation.function_name}:{violation.file_path}"
            )
        return 1

    print("guardrail_status:ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
