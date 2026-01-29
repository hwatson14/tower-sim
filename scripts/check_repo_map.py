#!/usr/bin/env python3
"""Validate repository structure against REPO_MAP.yaml."""
from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

import yaml

IGNORED_NAMES = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
}


def load_repo_map(repo_root: Path) -> dict:
    repo_map_path = repo_root / "REPO_MAP.yaml"
    try:
        data = yaml.safe_load(repo_map_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing REPO_MAP.yaml: {repo_map_path}") from exc
    if not isinstance(data, dict):
        raise SystemExit("REPO_MAP.yaml must parse to a mapping.")
    return data


def to_posix(path: Path) -> str:
    return path.as_posix()


def matches_any(path: str, patterns: list[str]) -> bool:
    path_obj = PurePosixPath(path)
    for pattern in patterns:
        candidates = {pattern}
        if "**/" in pattern:
            candidates.add(pattern.replace("**/", ""))
        if "/**/" in pattern:
            candidates.add(pattern.replace("/**/", "/"))
        if "/**" in pattern:
            candidates.add(pattern.replace("/**", ""))
        candidates.add(pattern.replace("**", "*"))
        for candidate in candidates:
            if candidate and path_obj.match(candidate):
                return True
    return False


def is_ignored(path: Path) -> bool:
    return any(part in IGNORED_NAMES for part in path.parts)


def is_exception(path: Path, exceptions: list[str]) -> bool:
    if not exceptions:
        return False
    rel_path = to_posix(path)
    return matches_any(rel_path, exceptions)


def check_top_level(repo_root: Path, config: dict, errors: list[str]) -> None:
    allowed_dirs = set(config["allowed_dirs"])
    allowed_files = set(config["allowed_files"])
    forbidden_dirs = set(config.get("forbidden_dirs", []))

    for entry in repo_root.iterdir():
        if entry.name in IGNORED_NAMES:
            continue
        if entry.is_dir():
            if entry.name in forbidden_dirs:
                errors.append(f"Forbidden top-level directory: {entry.name}")
            if entry.name not in allowed_dirs:
                errors.append(f"Unexpected top-level directory: {entry.name}")
        elif entry.is_file():
            if entry.name not in allowed_files:
                errors.append(f"Unexpected top-level file: {entry.name}")


def check_allowed_subdirs(base: Path, allowed_subdirs: list[str], errors: list[str]) -> None:
    if not base.exists():
        return
    for entry in base.iterdir():
        if entry.is_dir() and not is_ignored(entry):
            if entry.name not in allowed_subdirs:
                errors.append(
                    f"Unexpected subdirectory in {base.as_posix()}: {entry.name}"
                )


def check_directory_rules(
    repo_root: Path,
    base: Path,
    rules: dict,
    exceptions: list[str],
    errors: list[str],
) -> None:
    if not base.exists():
        return
    allowed = rules.get("allowed_file_globs", [])
    forbidden = rules.get("forbidden_file_globs", [])

    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if is_ignored(path) or is_exception(path.relative_to(repo_root), exceptions):
            continue
        rel_path = to_posix(path.relative_to(base))
        if allowed and not matches_any(rel_path, allowed):
            errors.append(f"Disallowed file in {base.as_posix()}: {rel_path}")
        if forbidden and matches_any(rel_path, forbidden):
            errors.append(f"Forbidden file in {base.as_posix()}: {rel_path}")


def is_snake_segment(segment: str) -> bool:
    return re.fullmatch(r"[a-z0-9_]+", segment) is not None


def check_naming_rules(
    repo_root: Path,
    config: dict,
    exceptions: list[str],
    errors: list[str],
) -> None:
    naming_rules = config.get("naming_rules", {})
    if not naming_rules.get("require_snake_case_filenames"):
        return

    forbidden_basenames = set(naming_rules.get("forbidden_base_filenames", []))
    allowed_top_level_files = set(config["top_level"]["allowed_files"])

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if is_ignored(path):
            continue
        rel_path = path.relative_to(repo_root)
        if rel_path.parts and rel_path.parts[0] == "reference":
            continue
        if rel_path.parts[:2] == ("tests", "fixtures"):
            continue
        if is_exception(rel_path, exceptions):
            continue
        if rel_path.parts and rel_path.parts[0] == "tables" and rel_path.name == "README.md":
            continue
        if rel_path.parts and rel_path.parts[0] == "tests_quarantine" and rel_path.name == "README.md":
            continue
        if len(rel_path.parts) == 1 and rel_path.name in allowed_top_level_files:
            continue

        name = path.name
        if name.startswith("."):
            continue
        segments = [segment for segment in name.split(".") if segment]
        if not segments:
            continue
        if segments[0] in forbidden_basenames:
            errors.append(
                f"Forbidden filename base '{segments[0]}' at {rel_path.as_posix()}"
            )
        if not all(is_snake_segment(segment) for segment in segments):
            errors.append(f"Non-snake_case filename: {rel_path.as_posix()}")


def check_generated_artifacts(
    repo_root: Path,
    config: dict,
    exceptions: list[str],
    errors: list[str],
) -> None:
    rules = config.get("generated_artifacts", {})
    forbidden = rules.get("forbidden_name_globs", [])
    allowed_paths = rules.get("allowed_paths_for_generated", [])

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if is_ignored(path) or is_exception(path.relative_to(repo_root), exceptions):
            continue
        rel_path = to_posix(path.relative_to(repo_root))
        if forbidden and matches_any(rel_path, forbidden):
            if not matches_any(rel_path, allowed_paths):
                errors.append(f"Generated artifact stored outside audit/: {rel_path}")


def check_file_count_caps(repo_root: Path, config: dict, errors: list[str]) -> None:
    caps = config.get("file_count_caps", {})
    if not caps.get("enabled", False):
        return

    for rel_path, cap in caps.get("caps", {}).items():
        base = repo_root / rel_path
        if not base.exists():
            continue
        count = sum(
            1
            for path in base.rglob("*")
            if path.is_file() and not is_ignored(path)
        )
        if count > cap:
            errors.append(
                f"File count cap exceeded for {rel_path}: {count} > {cap}"
            )


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = load_repo_map(repo_root)
    errors: list[str] = []
    exceptions = config.get("exceptions", {}).get("allow_paths", [])

    check_top_level(repo_root, config["top_level"], errors)

    tower_sim_dir = repo_root / "tower_sim"
    check_allowed_subdirs(tower_sim_dir, config["tower_sim"]["allowed_subdirs"], errors)

    for section in ["tower_sim", "tables", "reference", "audit", "tests", "tests_quarantine", "scripts"]:
        base = repo_root / section
        rules = config.get(section, {})
        check_directory_rules(repo_root, base, rules, exceptions, errors)

    check_naming_rules(repo_root, config, exceptions, errors)
    check_generated_artifacts(repo_root, config, exceptions, errors)
    check_file_count_caps(repo_root, config, errors)

    if errors:
        error_text = "\n".join(f"- {error}" for error in sorted(errors))
        raise SystemExit(f"REPO_MAP violations detected:\n{error_text}")

    print("REPO_MAP validation passed.")


if __name__ == "__main__":
    main()
