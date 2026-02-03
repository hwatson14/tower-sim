from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

from tower_sim.evaluators.max_wave import MaxWaveEvaluator
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.spec_loader import load_problem_spec


def run() -> Dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    ids_path = repo_root / "tests" / "fixtures" / "tower-sim-data" / "_IDS.csv"
    spec_path = repo_root / "tests" / "fixtures" / "specs" / "sample_spec.yaml"
    problem_spec = load_problem_spec(spec_path)
    ids_state = parse_ids(ids_path)
    return MaxWaveEvaluator().evaluate(problem_spec, ids_state)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MaxWaveEvaluator fixture.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if fail_closed=true.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    strict = args.strict or os.environ.get("STRICT") == "1"
    result = run()
    print(json.dumps(result, indent=2, sort_keys=True))
    if strict and result.get("fail_closed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
