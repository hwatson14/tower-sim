from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tower_sim.registry.static_v2_contract import summarize_v2_registry_status


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print V2 registry status summary and next steps."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    args = parser.parse_args()

    status = summarize_v2_registry_status()
    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))
        return 0

    summary = status["summary_status"]
    print("V2 registry summary status")
    for key in (
        "canonical_target_stats",
        "runtime_mechanic_parameters",
        "environment_parameters",
        "capabilities",
        "canonical_object_ids",
        "canonical_contributor_ids",
        "composite_targets",
        "blocked_or_unresolved_targets",
        "blocked_or_unresolved_legacy_names",
        "phase_b_coverage_accounting_complete",
    ):
        print(f"- {key}: {summary[key]}")

    print("\nNext:")
    for item in status["next"]:
        print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
