from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tower_sim.engines.perk_timeline_generator import generate_timeline  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--diagnostics", required=True)
    args = ap.parse_args()

    timeline, diag = generate_timeline(Path(args.policy))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.diagnostics).parent.mkdir(parents=True, exist_ok=True)

    Path(args.out).write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    Path(args.diagnostics).write_text(json.dumps(diag, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
