from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import yaml

CANONICAL_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]+$")


@dataclass(frozen=True)
class AuditItem:
    code: str
    message: str
    paths: Tuple[str, ...] = ()


@dataclass
class AuditReport:
    passes: List[AuditItem] = field(default_factory=list)
    warnings: List[AuditItem] = field(default_factory=list)
    failures: List[AuditItem] = field(default_factory=list)

    def add_pass(self, code: str, message: str, paths: Iterable[Path] = ()) -> None:
        self.passes.append(AuditItem(code=code, message=message, paths=_paths(paths)))

    def add_warning(self, code: str, message: str, paths: Iterable[Path] = ()) -> None:
        self.warnings.append(AuditItem(code=code, message=message, paths=_paths(paths)))

    def add_failure(self, code: str, message: str, paths: Iterable[Path] = ()) -> None:
        self.failures.append(AuditItem(code=code, message=message, paths=_paths(paths)))

    def to_dict(self) -> Dict[str, object]:
        return {
            "summary": {
                "passes": len(self.passes),
                "warnings": len(self.warnings),
                "failures": len(self.failures),
            },
            "passes": [item.__dict__ for item in self.passes],
            "warnings": [item.__dict__ for item in self.warnings],
            "failures": [item.__dict__ for item in self.failures],
        }

    def to_markdown(self) -> str:
        lines = [
            "# TowerSim Repo Audit",
            "",
            "## Summary",
            f"- Passes: {len(self.passes)}",
            f"- Warnings: {len(self.warnings)}",
            f"- Failures: {len(self.failures)}",
            "",
        ]
        lines.extend(_format_section("Passes", self.passes))
        lines.extend(_format_section("Warnings", self.warnings))
        lines.extend(_format_section("Failures", self.failures, include_recommendations=True))
        return "\n".join(lines)


@dataclass(frozen=True)
class NamingCatalog:
    canonical_ids: Set[str]
    categories: Dict[str, List[Dict[str, object]]]


def run_audit(repo_root: Path, strict: bool) -> AuditReport:
    report = AuditReport()

    naming_files = _find_naming_yaml_files(repo_root)
    naming_catalog = _check_naming_yaml(report, naming_files)

    known_ids = set(naming_catalog.canonical_ids)
    known_ids.update(_parse_stat_registry_ids(repo_root))

    _check_registry_references(report, repo_root, known_ids, naming_files)
    _check_tables(report, repo_root, strict)
    _check_modules(report, repo_root)

    if strict and report.failures:
        report.add_failure(
            "STRICT_FAILURE",
            "Strict mode enabled: failures present.",
        )

    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="TowerSim repository audit")
    parser.add_argument("--strict", action="store_true", help="Fail closed on warnings")
    parser.add_argument("--markdown", type=Path, help="Write Markdown report")
    parser.add_argument("--json", type=Path, dest="json_path", help="Write JSON report")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    report = run_audit(repo_root, args.strict)

    if args.markdown:
        args.markdown.write_text(report.to_markdown(), encoding="utf-8")
    if args.json_path:
        args.json_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    if args.strict and report.failures:
        return 2
    return 0


def _find_naming_yaml_files(repo_root: Path) -> List[Path]:
    candidates: List[Path] = []
    naming_dir = repo_root / "tables" / "registry"
    wiki_dir = repo_root / "tower_sim" / "loaders" / "wiki"
    for base in (naming_dir, wiki_dir):
        if base.exists():
            candidates.extend(sorted(base.rglob("*.yaml")))
    return candidates


def _check_naming_yaml(report: AuditReport, yaml_files: List[Path]) -> NamingCatalog:
    if not yaml_files:
        report.add_failure(
            "A_NAMING_MISSING",
            "No naming YAML files found.",
        )
        return NamingCatalog(canonical_ids=set(), categories={})

    canonical_ids: Set[str] = set()
    categories: Dict[str, List[Dict[str, object]]] = {}

    category_aliases: Dict[str, Dict[str, str]] = {}

    for yaml_file in yaml_files:
        try:
            payload = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            report.add_failure(
                "A_YAML_PARSE_ERROR",
                f"Failed to parse YAML: {exc}",
                paths=[yaml_file],
            )
            continue

        if not isinstance(payload, dict) or "categories" not in payload:
            report.add_failure(
                "A_YAML_SCHEMA",
                "Naming YAML missing 'categories' mapping.",
                paths=[yaml_file],
            )
            continue

        payload_categories = payload.get("categories")
        if not isinstance(payload_categories, dict):
            report.add_failure(
                "A_YAML_SCHEMA",
                "Naming YAML 'categories' is not a mapping.",
                paths=[yaml_file],
            )
            continue

        for category_name, entries in payload_categories.items():
            if not isinstance(entries, list):
                report.add_failure(
                    "A_CATEGORY_SCHEMA",
                    f"Category '{category_name}' entries should be a list.",
                    paths=[yaml_file],
                )
                continue
            categories.setdefault(category_name, []).extend(entries)

            alias_map = category_aliases.setdefault(category_name, {})
            for entry in entries:
                if not isinstance(entry, dict):
                    report.add_failure(
                        "A_ENTRY_SCHEMA",
                        f"Category '{category_name}' entry is not a mapping.",
                        paths=[yaml_file],
                    )
                    continue

                canonical_id = entry.get("canonical_id")
                if not isinstance(canonical_id, str):
                    report.add_failure(
                        "A_CANONICAL_ID_MISSING",
                        f"Missing canonical_id in category '{category_name}'.",
                        paths=[yaml_file],
                    )
                    continue

                if canonical_id in canonical_ids:
                    report.add_failure(
                        "A_CANONICAL_ID_DUPLICATE",
                        f"Duplicate canonical_id '{canonical_id}'.",
                        paths=[yaml_file],
                    )
                else:
                    canonical_ids.add(canonical_id)

                if not CANONICAL_ID_PATTERN.match(canonical_id):
                    report.add_failure(
                        "A_CANONICAL_ID_FORMAT",
                        f"Invalid canonical_id format: '{canonical_id}'.",
                        paths=[yaml_file],
                    )

                aliases = entry.get("aliases", [])
                if aliases is None:
                    aliases = []
                if not isinstance(aliases, list):
                    report.add_failure(
                        "A_ALIAS_SCHEMA",
                        f"Aliases for '{canonical_id}' should be a list.",
                        paths=[yaml_file],
                    )
                    continue

                for alias in aliases:
                    if not isinstance(alias, str):
                        report.add_failure(
                            "A_ALIAS_SCHEMA",
                            f"Alias for '{canonical_id}' must be a string.",
                            paths=[yaml_file],
                        )
                        continue
                    existing = alias_map.get(alias)
                    if existing and existing != canonical_id:
                        report.add_failure(
                            "A_ALIAS_DUPLICATE",
                            (
                                f"Alias '{alias}' maps to both '{existing}' and "
                                f"'{canonical_id}' in category '{category_name}'."
                            ),
                            paths=[yaml_file],
                        )
                    else:
                        alias_map[alias] = canonical_id

    if canonical_ids:
        report.add_pass(
            "A_NAMING_OK",
            f"Loaded {len(canonical_ids)} canonical IDs from naming YAML.",
            paths=yaml_files,
        )
    return NamingCatalog(canonical_ids=canonical_ids, categories=categories)


def _parse_stat_registry_ids(repo_root: Path) -> Set[str]:
    stat_registry_path = repo_root / "tower_sim" / "registry" / "stat_registry.py"
    if not stat_registry_path.exists():
        return set()
    content = stat_registry_path.read_text(encoding="utf-8")
    return set(re.findall(r'stat_id="([^"]+)"', content))


def _iter_reference_files(repo_root: Path) -> List[Path]:
    roots = [
        repo_root / "tower_sim" / "libs",
    ]
    exts = {".py"}
    files: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix in exts and path.is_file():
                files.append(path)
    for extra in (
        repo_root / "tower_sim" / "engines" / "modules.py",
        repo_root / "tower_sim" / "libs" / "modules_library.py",
    ):
        if extra.exists() and extra.suffix in exts:
            files.append(extra)

    return sorted(set(files))


def _check_registry_references(
    report: AuditReport,
    repo_root: Path,
    known_ids: Set[str],
    naming_files: List[Path],
) -> None:
    if not known_ids:
        report.add_warning(
            "B_NO_KNOWN_IDS",
            "No canonical IDs available for registry reference scan.",
        )
        return

    unknown_hits: Dict[Path, Set[str]] = {}
    for path in _iter_reference_files(repo_root):
        if path in naming_files:
            continue
        tokens = _extract_canonical_strings(path)
        unknown = {token for token in tokens if token not in known_ids}
        if unknown:
            unknown_hits[path] = unknown

    if unknown_hits:
        for path, tokens in unknown_hits.items():
            report.add_failure(
                "B_UNKNOWN_CANONICAL_ID",
                f"Unknown canonical IDs found: {sorted(tokens)}",
                paths=[path],
            )
    else:
        report.add_pass(
            "B_REGISTRY_OK",
            "No unknown canonical ID references detected.",
        )


def _check_tables(report: AuditReport, repo_root: Path, strict: bool) -> None:
    tables_dir = repo_root / "tables"
    if not tables_dir.exists():
        report.add_failure(
            "C_TABLES_MISSING",
            "Expected tables directory is missing.",
            paths=[tables_dir],
        )
        return

    csvs = sorted(path.name for path in tables_dir.glob("*.csv"))
    report.add_pass(
        "C_TABLES_PRESENT",
        f"Found {len(csvs)} CSV table(s).",
        paths=[tables_dir],
    )

    expected = "labs_values_v1.csv"
    expected_path = tables_dir / expected
    if not expected_path.exists():
        labs_complete = _architecture_labs_complete(repo_root)
        if strict and labs_complete:
            report.add_failure(
                "C_LABS_VALUES_MISSING",
                "labs_values_v1.csv missing but labs stage marked complete.",
                paths=[expected_path],
            )
        else:
            report.add_warning(
                "C_LABS_VALUES_MISSING",
                "labs_values_v1.csv missing (not strict or labs stage incomplete).",
                paths=[expected_path],
            )


def _architecture_labs_complete(repo_root: Path) -> bool:
    architecture_path = repo_root / "ARCHITECTURE.md"
    if not architecture_path.exists():
        return False
    for line in architecture_path.read_text(encoding="utf-8").splitlines():
        normalized = line.strip().lower()
        if normalized.startswith("- [x]") and "labs" in normalized and "value" in normalized:
            return True
    return False


def _check_modules(report: AuditReport, repo_root: Path) -> None:
    key_modules = [
        "tower_sim/registry/stat_registry.py",
        "tower_sim/util/statbook.py",
        "tower_sim/libs/workshop_lib.py",
        "tower_sim/libs/labs_lib.py",
        "tower_sim/libs/modules_lib.py",
        "tower_sim/libs/uw_lib.py",
        "tower_sim/libs/cards_lib.py",
        "tower_sim/libs/modules_library.py",
    ]

    tests_root = repo_root / "tests"
    test_text = ""
    if tests_root.exists():
        test_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(tests_root.rglob("*.py"))
        )

    for rel_path in key_modules:
        path = repo_root / rel_path
        if not path.exists():
            report.add_failure(
                "D_MODULE_MISSING",
                f"Key module missing: {rel_path}",
                paths=[path],
            )
            continue

        if _is_stub_module(path):
            report.add_failure(
                "D_MODULE_STUB",
                f"Key module appears to be a stub: {rel_path}",
                paths=[path],
            )
        else:
            report.add_pass(
                "D_MODULE_IMPLEMENTED",
                f"Key module implemented: {rel_path}",
                paths=[path],
            )

        module_name = rel_path.replace("/", ".").removesuffix(".py")
        if module_name and module_name not in test_text:
            report.add_warning(
                "D_MODULE_TEST_MISSING",
                f"No tests referencing module: {module_name}",
                paths=[tests_root],
            )


def _is_stub_module(path: Path) -> bool:
    import ast

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return True

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False

    allowed = (ast.Import, ast.ImportFrom, ast.Pass)
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        if isinstance(node, allowed):
            continue
        return False
    return True


def _paths(paths: Iterable[Path]) -> Tuple[str, ...]:
    return tuple(str(path) for path in paths)


def _extract_canonical_strings(path: Path) -> Set[str]:
    import ast

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()

    tokens: Set[str] = set()
    tokens.update(_extract_from_dicts(tree))
    tokens.update(_extract_from_assignments(tree))
    return tokens


def _extract_from_dicts(tree: "ast.AST") -> Set[str]:
    import ast

    tokens: Set[str] = set()
    key_names = {"canonical_id", "stat_id", "stat_ids"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                continue
            if key.value not in key_names:
                continue
            tokens.update(_extract_strings(value))
    return tokens


def _extract_from_assignments(tree: "ast.AST") -> Set[str]:
    import ast

    tokens: Set[str] = set()
    list_names = {"CANONICAL_IDS", "STAT_IDS"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id in list_names
            for target in node.targets
        ):
            continue
        tokens.update(_extract_strings(node.value))
    return tokens


def _extract_strings(node: "ast.AST") -> Set[str]:
    import ast

    tokens: Set[str] = set()
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        if CANONICAL_ID_PATTERN.match(node.value):
            tokens.add(node.value)
        return tokens
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for element in node.elts:
            tokens.update(_extract_strings(element))
    return tokens


def _format_section(
    title: str,
    items: List[AuditItem],
    include_recommendations: bool = False,
) -> List[str]:
    lines = [f"## {title}", ""]
    if not items:
        lines.append("- None")
        lines.append("")
        return lines
    for item in items:
        path_text = f" ({', '.join(item.paths)})" if item.paths else ""
        lines.append(f"- **{item.code}**: {item.message}{path_text}")
        if include_recommendations:
            context = _failure_context(item)
            recommendation = _failure_recommendation(item)
            if context:
                lines.append(f"  - Context: {context}")
            if recommendation:
                lines.append(f"  - Suggested fix: {recommendation}")
    lines.append("")
    return lines


def _failure_context(item: AuditItem) -> Optional[str]:
    if item.paths:
        return f"Paths: {', '.join(item.paths)}"
    return {
        "A_ALIAS_DUPLICATE": "Naming catalog alias list within a category.",
        "A_CANONICAL_ID_DUPLICATE": "Naming catalog canonical_id registry.",
        "A_CANONICAL_ID_FORMAT": "Naming catalog canonical_id formatting.",
        "A_CANONICAL_ID_MISSING": "Naming catalog entries missing canonical_id.",
        "A_CATEGORY_SCHEMA": "Naming catalog category schema.",
        "A_ENTRY_SCHEMA": "Naming catalog entry schema.",
        "A_NAMING_MISSING": "Naming catalog YAML discovery.",
        "A_YAML_PARSE_ERROR": "Naming catalog YAML parsing.",
        "A_YAML_SCHEMA": "Naming catalog YAML schema.",
        "A_ALIAS_SCHEMA": "Naming catalog aliases schema.",
        "B_UNKNOWN_CANONICAL_ID": "Registry mapping references.",
        "C_TABLES_MISSING": "Canonical tables directory.",
        "C_LABS_VALUES_MISSING": "Canonical labs table presence.",
        "D_MODULE_MISSING": "Key module inventory.",
        "D_MODULE_STUB": "Key module implementation status.",
        "STRICT_FAILURE": "Strict mode enforcement.",
    }.get(item.code)


def _failure_recommendation(item: AuditItem) -> Optional[str]:
    return {
        "A_ALIAS_DUPLICATE": "Remove or rename duplicate aliases so each maps to one canonical_id.",
        "A_CANONICAL_ID_DUPLICATE": "Deduplicate canonical_id entries in the naming catalog.",
        "A_CANONICAL_ID_FORMAT": "Update canonical_id values to match ^[A-Z][A-Z0-9_]+$.",
        "A_CANONICAL_ID_MISSING": "Add canonical_id fields to each naming catalog entry.",
        "A_CATEGORY_SCHEMA": "Ensure category entries are YAML lists of mappings.",
        "A_ENTRY_SCHEMA": "Ensure each category entry is a mapping with canonical_id and names.",
        "A_NAMING_MISSING": "Add a naming YAML (e.g., tables/registry/catalog.yaml) or restore it.",
        "A_YAML_PARSE_ERROR": "Fix YAML syntax errors in the naming catalog.",
        "A_YAML_SCHEMA": "Add a top-level 'categories' mapping in naming YAML.",
        "A_ALIAS_SCHEMA": "Ensure aliases is a list of strings (or omit for none).",
        "B_UNKNOWN_CANONICAL_ID": "Add missing canonical IDs to naming YAML or stat registry, or fix typos.",
        "C_TABLES_MISSING": "Create tables/ and add the canonical CSV tables.",
        "C_LABS_VALUES_MISSING": "Add labs_values_v1.csv with provenance or update architecture status.",
        "D_MODULE_MISSING": "Add the missing key module file or remove it from the audit list.",
        "D_MODULE_STUB": "Implement the module beyond imports/docstrings/passes.",
        "STRICT_FAILURE": "Resolve failures above or rerun without --strict.",
    }.get(item.code)


if __name__ == "__main__":
    sys.exit(main())
