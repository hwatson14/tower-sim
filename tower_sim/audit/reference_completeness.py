from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable

import yaml


EXCLUDED_DIRS = {"reference", "tests"}
STEP1_DIR = Path("reference/step1_dump_docs")


REQUIRED_TABLES: Dict[str, list[str]] = {
    "bc_heat": [
        "battle_conditions.csv",
        "heat.csv",
        "battle_condition_magnitudes.csv",
        "tier14_21_battle_conditions.csv",
        "heat_wave_scalar.csv",
    ],
    "wave_damage": ["tier_wave_damage.csv", "tournament_wave_damage.csv"],
    "tournament_boss_freq": ["tournament_more_bosses_static.csv"],
    "dag_inputs": ["tiers.csv", "dag.json"],
}


@dataclass(frozen=True)
class CategoryReport:
    status: str
    runtime_paths: list[str]
    step1_only_paths: list[str]
    missing_paths: list[str]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "runtime_paths": self.runtime_paths,
            "step1_only_paths": self.step1_only_paths,
            "missing_paths": self.missing_paths,
        }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_runtime_path(path: Path) -> bool:
    return not any(part in EXCLUDED_DIRS for part in path.parts)


def _find_runtime_paths(filename: str) -> list[Path]:
    repo_root = _repo_root()
    return [path for path in repo_root.rglob(filename) if _is_runtime_path(path)]


def _find_step1_paths(filename: str) -> list[Path]:
    repo_root = _repo_root()
    step1_root = repo_root / STEP1_DIR
    if not step1_root.exists():
        return []
    return list(step1_root.rglob(filename))


def _classify_paths(filenames: Iterable[str]) -> CategoryReport:
    repo_root = _repo_root()
    runtime_paths: list[str] = []
    step1_only_paths: list[str] = []
    missing_paths: list[str] = []

    for filename in filenames:
        runtime_matches = _find_runtime_paths(filename)
        if runtime_matches:
            runtime_paths.extend(
                str(path.relative_to(repo_root)) for path in sorted(runtime_matches)
            )
            continue
        step1_matches = _find_step1_paths(filename)
        if step1_matches:
            step1_only_paths.extend(
                str(path.relative_to(repo_root)) for path in sorted(step1_matches)
            )
            continue
        missing_paths.append(filename)

    if missing_paths:
        status = "missing"
    elif step1_only_paths:
        status = "step1-only"
    else:
        status = "runtime"

    return CategoryReport(
        status=status,
        runtime_paths=runtime_paths,
        step1_only_paths=step1_only_paths,
        missing_paths=missing_paths,
    )


def build_report() -> Dict[str, CategoryReport]:
    report: Dict[str, CategoryReport] = {}
    for category, filenames in REQUIRED_TABLES.items():
        report[category] = _classify_paths(filenames)
    return report


def _format_report(report: Dict[str, CategoryReport]) -> str:
    lines = [
        "# Reference Completeness Report",
        "",
        "This report inventories required runtime tables and classifies them as:",
        "- **runtime**: present outside `reference/` and test fixtures.",
        "- **step1-only**: present only under `reference/step1_dump_docs/...`.",
        "- **missing**: not present anywhere in the repo.",
        "",
        "## Manifest (machine-readable)",
        "",
        "```yaml",
    ]
    manifest = {
        "required_tables": {
            category: data.to_dict() for category, data in report.items()
        }
    }
    lines.append(yaml.safe_dump(manifest, sort_keys=False).strip())
    lines.extend(["```", ""])
    return "\n".join(lines)


def write_report(path: Path) -> None:
    report = build_report()
    path.write_text(_format_report(report), encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the reference completeness report."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("audit/reference_completeness_report.md"),
        help="Output path for the report.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    write_report(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
