from __future__ import annotations

import argparse
import json
from pathlib import Path

from tower_sim.run.api import TASK_MAX_WAVE
from tower_sim.run.runner import run


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Canonical TowerSim runner entrypoint.")
    parser.add_argument(
        "task",
        nargs="?",
        choices=[TASK_MAX_WAVE],
        default=TASK_MAX_WAVE,
        help=argparse.SUPPRESS,
    )
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
    result = run(spec_path=args.spec, patch_path=args.patch, ids_path=args.ids)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
