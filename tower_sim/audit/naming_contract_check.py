from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from tower_sim.loaders.account_snapshot_compiler import compile_account_snapshot
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.registry.naming_contract import (
    named_entity_alias_maps,
    validate_account_snapshot_naming,
    validate_named_entity_coverage,
    validate_registry_parity,
)
from tower_sim.registry.stat_registry import default_registry


def run_naming_contract_check(*, ids_path: Path | None = None) -> Dict[str, Any]:
    parity_errors = list(validate_registry_parity(default_registry()))
    entity_errors = list(validate_named_entity_coverage())

    snapshot_errors = []
    snapshot_loaded = False
    if ids_path is not None:
        snapshot = compile_account_snapshot(parse_ids(ids_path))
        snapshot_loaded = True
        snapshot_errors = list(validate_account_snapshot_naming(snapshot))

    category_sizes = {
        category: len(alias_map) for category, alias_map in named_entity_alias_maps().items()
    }

    all_errors = sorted(set(parity_errors + entity_errors + snapshot_errors))
    return {
        "status": "ok" if not all_errors else "error",
        "errors": all_errors,
        "parity_errors": parity_errors,
        "entity_errors": entity_errors,
        "snapshot_errors": snapshot_errors,
        "snapshot_loaded": snapshot_loaded,
        "entity_category_sizes": category_sizes,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate repository naming contract coverage.")
    parser.add_argument("--ids", type=Path, default=None, help="Optional path to _IDS.csv for snapshot naming validation.")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = run_naming_contract_check(ids_path=args.ids)
    payload = json.dumps(result, indent=2, sort_keys=True)
    print(payload)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    if args.strict and result["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
