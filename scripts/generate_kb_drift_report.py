#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml

from v3.kb_access import content_sha256, load_yaml, resolve_kb_location

_LOCK_PATH = Path("v3/kb_contract_lock.yaml")
_REPORT_DEFAULT = Path("audit/kb_drift_report.json")


def _load_lock() -> dict[str, str]:
    payload = yaml.safe_load(_LOCK_PATH.read_text(encoding="utf-8"))
    contracts = payload.get("contracts") if isinstance(payload, dict) else None
    if not isinstance(contracts, dict):
        raise SystemExit("Invalid or missing v3/kb_contract_lock.yaml contracts map.")
    return {str(k): str(v) for k, v in contracts.items()}


def run_report() -> dict:
    lock = _load_lock()
    location = resolve_kb_location()
    drifts: list[dict[str, str]] = []
    for rel_path, expected in lock.items():
        observed = content_sha256(rel_path, location=location)
        if observed != expected:
            drifts.append(
                {
                    "path": rel_path,
                    "expected_sha256": expected,
                    "observed_sha256": observed,
                }
            )

    # Optional semantic check for naming contract kind.
    naming_doc = load_yaml("kb/global-rules/contracts/naming-contract.yaml", location=location)
    naming_kind = str(naming_doc.get("kind", "")).strip()
    semantic_errors: list[str] = []
    if naming_kind != "naming_contract":
        semantic_errors.append(f"naming_contract_kind_mismatch:{naming_kind}")

    return {
        "status": "ok" if not drifts and not semantic_errors else "drift",
        "kb_mode": location.mode,
        "kb_root": str(location.root),
        "hash_drifts": drifts,
        "semantic_errors": semantic_errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate KB drift report for locked contract surfaces.")
    parser.add_argument("--output", type=Path, default=_REPORT_DEFAULT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    report = run_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))

    if args.strict and report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
