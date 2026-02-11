from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict


if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

from tower_sim.evaluators.max_wave import MaxWaveEvaluator
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.run.spec_loader import load_problem_spec


def _resolve_default_fixture_paths() -> tuple[Path, Path]:
    repo_root = Path(__file__).resolve().parents[2]
    ids_path = repo_root / "tests" / "fixtures" / "tower-sim-data" / "_IDS.csv"
    spec_path = repo_root / "tests" / "fixtures" / "specs" / "sample_spec.yaml"
    if not ids_path.exists() or not spec_path.exists():
        raise FileNotFoundError(
            "Default runner fixtures are unavailable. Pass --ids and --spec explicitly."
        )
    return ids_path, spec_path


def run(ids_path: Path | None = None, spec_path: Path | None = None) -> Dict[str, Any]:
    if ids_path is None or spec_path is None:
        default_ids_path, default_spec_path = _resolve_default_fixture_paths()
        ids_path = ids_path or default_ids_path
        spec_path = spec_path or default_spec_path

    if not ids_path.exists():
        raise FileNotFoundError(f"IDS CSV not found: {ids_path}")
    if not spec_path.exists():
        raise FileNotFoundError(f"Problem spec not found: {spec_path}")

    problem_spec = load_problem_spec(spec_path)
    ids_raw = parse_ids(ids_path)
    snapshot = compile_account_snapshot(ids_raw)
    return MaxWaveEvaluator().evaluate(problem_spec, snapshot)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MaxWaveEvaluator fixture.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if fail_closed=true.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON path (default: out/runner_output.json).",
    )
    parser.add_argument(
        "--ids",
        type=Path,
        help="Path to IDS CSV. Defaults to test fixture when available.",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        help="Path to ProblemSpec YAML/JSON. Defaults to test fixture when available.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    strict = args.strict or os.environ.get("STRICT") == "1"
    result = run(ids_path=args.ids, spec_path=args.spec)
    repo_root = Path(__file__).resolve().parents[2]
    output_path = args.output or (repo_root / "out" / "runner_output.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(f"Wrote {output_path}")
    print(json.dumps(result, indent=2, sort_keys=True))
    if strict and result.get("fail_closed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
