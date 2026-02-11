from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from tower_sim.engines.stat_input_compiler import compile_full_stat_inputs
from tower_sim.evaluators.ehp_stat_evaluator import evaluate_stats
from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ep_export_loader import load_ep_export_dataset
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.spec_loader import load_problem_spec
from tower_sim.registry.naming_contract import resolve_stat_id, validate_registry_parity
from tower_sim.registry.stat_registry import default_registry




_DECISIVE_EHP_KEYS: Dict[str, str] = {
    "health": "Health",
    "health_regen": "Health Regen",
    "defense_percent": "Defense %",
    "wall_health": "Wall Health",
    "wall_regen": "Wall Regen",
}

def _relative_delta(expected: float, actual: float) -> float:
    denom = max(abs(expected), 1.0)
    return abs(expected - actual) / denom


def _build_statbook_value_map(ids_snapshot) -> Dict[str, float]:
    compiled = compile_full_stat_inputs(ids_snapshot)
    values: Dict[str, float] = {}
    for stat_input in compiled.stat_inputs:
        if stat_input.phase.value != "end_of_run":
            continue
        if stat_input.derived_value is not None:
            values[stat_input.stat_id] = float(stat_input.derived_value)
            continue

        base_value = stat_input.base_value or 0.0
        loadout_delta = stat_input.loadout_delta or 0.0
        enhancement_multiplier = stat_input.enhancement_multiplier or 1.0
        tier_delta = stat_input.tier_rule_delta or 0.0
        tier_multiplier = stat_input.tier_rule_multiplier or 1.0
        values[stat_input.stat_id] = (
            (base_value + loadout_delta) * enhancement_multiplier + tier_delta
        ) * tier_multiplier
    return values


def verify_final_stats_against_ep_export(
    *,
    ids_path: Path,
    spec_path: Path,
    suite: str = "ehp",
    tolerance: float = 0.01,
) -> Dict[str, Any]:
    dataset = load_ep_export_dataset()
    parity_errors = validate_registry_parity(default_registry())
    if parity_errors:
        raise ValueError(f"Registry/naming parity failed: {list(parity_errors)}")
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
    decisive_lineage: List[Dict[str, Any]] = []

    for row in dataset.rows:
        if row.suite != suite:
            continue
        vp = row.verification_path
        actual: float | None
        if vp.startswith("ehp_slice.stats.") or vp.startswith("ehp_eval.stats."):
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

        if suite == "ehp" and row.key in _DECISIVE_EHP_KEYS:
            expected_stat_id = resolve_stat_id(_DECISIVE_EHP_KEYS[row.key])
            if not vp.endswith(f".{expected_stat_id}"):
                unresolved.append(
                    {
                        "key": row.key,
                        "verification_path": row.verification_path,
                        "reason": f"lineage_mismatch_expected:{expected_stat_id}",
                    }
                )
            decisive_lineage.append(
                {
                    "key": row.key,
                    "alias": _DECISIVE_EHP_KEYS[row.key],
                    "expected_stat_id": expected_stat_id,
                    "verification_path": row.verification_path,
                }
            )

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

    if suite == "ehp":
        present = {entry["key"] for entry in decisive_lineage}
        expected = set(_DECISIVE_EHP_KEYS)
        if present != expected:
            missing_keys = sorted(expected - present)
            raise ValueError(f"Decisive lineage keys missing from parity coverage: {missing_keys}")
        lineage_errors = [item for item in unresolved if str(item.get("reason", "")).startswith("lineage_mismatch_expected:")]
        if lineage_errors:
            raise ValueError(f"Decisive lineage gate failed: {lineage_errors}")

    return {
        "suite": suite,
        "preset": expected_preset,
        "spec_mode": scenario_mode,
        "tolerance": tolerance,
        "compared_rows": compared,
        "unresolved_rows": unresolved,
        "decisive_lineage": decisive_lineage,
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
