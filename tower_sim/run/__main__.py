from __future__ import annotations

import argparse
import json
from pathlib import Path

from tower_sim.run import runner


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Canonical TowerSim runner entrypoint.")
    parser.add_argument("task", choices=["MAX_WAVE"], help="Canonical task to execute.")
    parser.add_argument("--spec", type=Path, required=True, help="Problem spec YAML path.")
    parser.add_argument(
        "--patch",
        type=Path,
        default=None,
        help="Optional YAML patch applied as a pure overlay before execution.",
    )
    parser.add_argument(
        "--ids",
        type=Path,
        default=None,
        help="Path to _IDS.csv (defaults to canonical loader fallback).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.task != "MAX_WAVE":
        raise ValueError(f"Unsupported task: {args.task}")
    result = runner.run(spec_path=args.spec, patch_path=args.patch, ids_path=args.ids)
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"Wrote {runner.OUT_MAX_WAVE_PATH}")
    print(f"Wrote {runner.OUT_LINEAGE_PATH}")


if __name__ == "__main__":
    main()
