from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from tower_sim.audit.naming_contract_check import run_naming_contract_check
from tower_sim.audit.stat_lineage_report import load_manifest, summarize_manifest
from tower_sim.registry.ep_formula_registry import MechanicsManifestError, load_active_mechanics_pack


def run_wiring_health_check(
    *,
    ids_path: Path,
    lineage_manifest_path: Path,
    max_required_max_wave_gaps: int | None = None,
    max_total_missing_pairs: int | None = None,
) -> Dict[str, Any]:
    checks: Dict[str, Any] = {}

    naming = run_naming_contract_check(ids_path=ids_path)
    checks["naming_contract"] = naming

    lineage_summary = summarize_manifest(load_manifest(lineage_manifest_path))
    checks["lineage_summary"] = lineage_summary

    try:
        active_pack = load_active_mechanics_pack()
        mechanics_manifest = {
            "status": "ok",
            "active_pack": active_pack.pack_id,
            "pack_path": str(active_pack.pack_path),
        }
    except MechanicsManifestError as exc:
        mechanics_manifest = {
            "status": "error",
            "error": str(exc),
        }
    checks["mechanics_manifest"] = mechanics_manifest

    violations: list[str] = []
    if naming["status"] != "ok":
        violations.append("naming_contract")
    if mechanics_manifest["status"] != "ok":
        violations.append("mechanics_manifest")

    if max_required_max_wave_gaps is not None:
        required_gap_count = int(lineage_summary["required_max_wave_gap_count"])
        if required_gap_count > max_required_max_wave_gaps:
            violations.append(
                "lineage_required_max_wave_gap_count"
                f"({required_gap_count}>{max_required_max_wave_gaps})"
            )

    if max_total_missing_pairs is not None:
        total_missing_pairs = int(lineage_summary["total_missing_pairs"])
        if total_missing_pairs > max_total_missing_pairs:
            violations.append(
                "lineage_total_missing_pairs"
                f"({total_missing_pairs}>{max_total_missing_pairs})"
            )

    return {
        "status": "ok" if not violations else "error",
        "violations": violations,
        "checks": checks,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run deterministic wiring-health checks (naming parity + lineage manifest + mechanics manifest) "
            "and emit a single status payload."
        )
    )
    parser.add_argument(
        "--ids",
        type=Path,
        default=Path("tests/fixtures/tower-sim-data/_IDS.csv"),
        help="Path to IDS snapshot CSV for naming contract validation.",
    )
    parser.add_argument(
        "--lineage-manifest",
        type=Path,
        default=Path("out/stat_lineage_manifest_latest.json"),
        help="Path to stat lineage manifest JSON.",
    )
    parser.add_argument(
        "--max-required-max-wave-gaps",
        type=int,
        default=None,
        help="Optional fail threshold for required_max_wave_gap_count.",
    )
    parser.add_argument(
        "--max-total-missing-pairs",
        type=int,
        default=None,
        help="Optional fail threshold for total_missing_pairs.",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = run_wiring_health_check(
        ids_path=args.ids,
        lineage_manifest_path=args.lineage_manifest,
        max_required_max_wave_gaps=args.max_required_max_wave_gaps,
        max_total_missing_pairs=args.max_total_missing_pairs,
    )
    payload = json.dumps(result, indent=2, sort_keys=True)
    print(payload)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    if args.strict and result["status"] != "ok":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
