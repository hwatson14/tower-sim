from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from tower_sim.engines.statbook_builder import build_statbook
from tower_sim.evaluators.ehp_stat_evaluator import evaluate_stats
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ep_export_loader import load_ep_export_dataset
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.spec_loader import load_problem_spec


def _relative_delta(expected: float, actual: float) -> float:
    denom = max(abs(expected), 1.0)
    return abs(expected - actual) / denom


def _build_statbook_value_map(ids_snapshot) -> Dict[str, float]:
    statbook = build_statbook(ids_snapshot)
    values: Dict[str, float] = {}
    for row in statbook.rows:
        if row.final_value is None:
            continue
        values.setdefault(row.stat_id, float(row.final_value))
    return values


def verify_final_stats_against_ep_export(
    *,
    ids_path: Path,
    spec_path: Path,
    suite: str = "ehp",
    tolerance: float = 0.01,
) -> Dict[str, Any]:
    dataset = load_ep_export_dataset()
    if suite not in dataset.verification_presets:
        raise ValueError(f"Unknown EP export suite {suite!r}.")

    spec = load_problem_spec(spec_path)
    expected_preset = dataset.verification_presets[suite]
    scenario_mode = spec.scenario.mode.lower()
    if scenario_mode != expected_preset:
        raise ValueError(
            f"Preset mismatch for suite {suite!r}: spec.mode={scenario_mode!r}, "
            f"ep_export_preset={expected_preset!r}."
        )

    ids_snapshot = compile_account_snapshot(parse_ids(ids_path))
    statbook_values = _build_statbook_value_map(ids_snapshot)
    ehp_stats = evaluate_stats(
        ids_snapshot,
        ["tower_hp", "tower_regen", "def_pct", "wall_hp", "wall_regen"],
        allow_out_of_scope=True,
    )

    compared: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []

    for row in dataset.rows:
        if row.suite != suite:
            continue
        vp = row.verification_path
        actual: float | None
        if vp.startswith("ehp_slice.stats."):
            stat_key = vp.split(".")[-1]
            actual = ehp_stats.get(stat_key)
        elif vp.startswith("stat_inputs."):
            stat_id = vp.split(".", 1)[1]
            actual = statbook_values.get(stat_id)
        else:
            unresolved.append(
                {
                    "key": row.key,
                    "verification_path": row.verification_path,
                    "reason": "unsupported_verification_path",
                }
            )
            continue

        if actual is None:
            unresolved.append(
                {
                    "key": row.key,
                    "verification_path": row.verification_path,
                    "reason": "missing_runtime_value",
                }
            )
            continue

        expected = float(row.value_numeric)
        rel = _relative_delta(expected, float(actual))
        compared.append(
            {
                "key": row.key,
                "verification_path": row.verification_path,
                "expected": expected,
                "actual": float(actual),
                "relative_delta": rel,
                "within_tolerance": rel <= tolerance,
            }
        )

    if not compared:
        raise ValueError(f"No EP export rows were comparable for suite {suite!r}.")

    mismatches = [item for item in compared if not item["within_tolerance"]]
    return {
        "suite": suite,
        "preset": expected_preset,
        "spec_mode": scenario_mode,
        "tolerance": tolerance,
        "compared_rows": compared,
        "unresolved_rows": unresolved,
        "mismatch_count": len(mismatches),
        "matched_count": len(compared) - len(mismatches),
        "status": "validated" if not mismatches else "mismatch",
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare end-of-run final stats against EP export rows for a suite."
    )
    parser.add_argument("--ids", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--suite", default="ehp")
    parser.add_argument("--tolerance", type=float, default=0.01)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = verify_final_stats_against_ep_export(
        ids_path=args.ids,
        spec_path=args.spec,
        suite=args.suite,
        tolerance=args.tolerance,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.strict and result["status"] != "validated":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
