"""naming_contract_check.py – CLI audit tool for the TowerSim naming contract.

Adapted from archive/tower_sim/audit/naming_contract_check.py.

Usage:
    python scripts/naming_contract_check.py
    python scripts/naming_contract_check.py --output /tmp/naming_check.json
    python scripts/naming_contract_check.py --ids input/IDS.csv --strict
    python scripts/naming_contract_check.py --ids input/IDS.csv --output out/naming_check.json --strict
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repo root is on the path when run as a script.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from registry.naming_contract import (
    validate_registry_parity,
    validate_named_entity_coverage,
    validate_account_snapshot_naming,
    named_entity_alias_maps,
)


def run_naming_contract_check(ids_snapshot=None) -> dict:
    """Run all naming contract checks and return a structured result dict.

    Args:
        ids_snapshot: Optional AccountState parsed from IDS.csv.  When
            provided, account-snapshot naming is also validated.

    Returns:
        dict with keys:
            status          – "ok" or "error"
            all_errors      – sorted list of error strings
            parity_errors   – registry parity errors only
            entity_errors   – named-entity coverage errors only
            snapshot_errors – account-snapshot naming errors (empty if no snapshot)
            snapshot_loaded – True if ids_snapshot was provided
            entity_category_sizes – {category: size} mapping
    """
    parity_errors = list(validate_registry_parity())
    entity_errors = list(validate_named_entity_coverage())
    snapshot_errors: list[str] = []

    if ids_snapshot is not None:
        snapshot_errors = list(
            validate_account_snapshot_naming(
                ids_snapshot,
                strict_categories=(
                    "labs", "workshop", "cards", "uws",
                    "bots", "bot_attributes", "modules", "module_substats",
                ),
            )
        )

    all_errors = sorted(set(parity_errors + entity_errors + snapshot_errors))
    entity_sizes = {
        category: len(alias_map)
        for category, alias_map in named_entity_alias_maps().items()
    }

    return {
        "status": "error" if all_errors else "ok",
        "all_errors": all_errors,
        "parity_errors": sorted(parity_errors),
        "entity_errors": sorted(entity_errors),
        "snapshot_errors": sorted(snapshot_errors),
        "snapshot_loaded": ids_snapshot is not None,
        "entity_category_sizes": entity_sizes,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate TowerSim naming contract against KB contracts and catalog."
    )
    parser.add_argument(
        "--ids",
        metavar="PATH",
        help="Path to an IDS.csv file to validate account-snapshot naming.",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Write JSON result to this file path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any errors are found.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    ids_snapshot = None
    if args.ids:
        ids_path = Path(args.ids)
        if not ids_path.exists():
            print(f"ERROR: IDS file not found: {ids_path}", file=sys.stderr)
            sys.exit(1)
        try:
            from parsers.ids_parser import parse_ids
            from compilers.account_state_compiler import compile_account_state
            raw = parse_ids(ids_path)
            ids_snapshot = compile_account_state(raw)
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: Could not load IDS snapshot: {exc}", file=sys.stderr)

    result = run_naming_contract_check(ids_snapshot=ids_snapshot)
    output_json = json.dumps(result, indent=2)
    print(output_json)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_json, encoding="utf-8")
        print(f"Result written to {out_path}", file=sys.stderr)

    if args.strict and result["status"] == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
