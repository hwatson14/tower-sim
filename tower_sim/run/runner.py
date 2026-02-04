from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

from tower_sim.evaluators.max_wave import MaxWaveEvaluator
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.run.spec_loader import load_problem_spec


def run() -> Dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    ids_path = repo_root / "tests" / "fixtures" / "tower-sim-data" / "_IDS.csv"
    spec_path = repo_root / "tests" / "fixtures" / "specs" / "sample_spec.yaml"
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
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    strict = args.strict or os.environ.get("STRICT") == "1"
    result = run()
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
