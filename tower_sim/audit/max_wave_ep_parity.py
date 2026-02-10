from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from tower_sim.loaders.ep_export_loader import extract_max_wave_targets, load_ep_export_dataset


def validate_runner_against_ep_export(
    *,
    runner_output_path: Path,
    suite: str,
    tolerance: float = 0.0,
    allow_missing_targets: bool = True,
) -> Dict[str, Any]:
    payload = json.loads(runner_output_path.read_text(encoding="utf-8"))
    if "w_max" not in payload:
        raise ValueError(f"Runner output missing required key 'w_max': {runner_output_path}")

    runner_wmax = float(payload["w_max"])

    dataset = load_ep_export_dataset()
    targets = extract_max_wave_targets(dataset)
    if not targets:
        reason = "EP export has no max-wave rows; max-wave parity check skipped."
        if allow_missing_targets:
            return {
                "status": "skipped_missing_targets",
                "suite": suite,
                "reason": reason,
                "runner_w_max": runner_wmax,
            }
        raise ValueError(reason)

    if suite not in targets:
        raise ValueError(
            f"EP export max-wave targets missing suite {suite!r}; available suites={sorted(targets.keys())}"
        )

    target_wmax = float(targets[suite])
    delta = abs(runner_wmax - target_wmax)
    if delta > tolerance:
        raise ValueError(
            f"Max-wave parity mismatch for suite {suite!r}: runner={runner_wmax}, "
            f"ep_export={target_wmax}, tolerance={tolerance}"
        )

    return {
        "status": "validated",
        "suite": suite,
        "runner_w_max": runner_wmax,
        "ep_export_w_max": target_wmax,
        "delta": delta,
        "tolerance": tolerance,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate max-wave runner output against EP export max-wave rows."
    )
    parser.add_argument("--runner-output", type=Path, required=True)
    parser.add_argument("--suite", default="ehp")
    parser.add_argument("--tolerance", type=float, default=0.0)
    parser.add_argument(
        "--allow-missing-targets",
        action="store_true",
        help="Treat missing EP max-wave rows as an explicit skip instead of failure.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = validate_runner_against_ep_export(
        runner_output_path=args.runner_output,
        suite=args.suite,
        tolerance=args.tolerance,
        allow_missing_targets=args.allow_missing_targets,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
