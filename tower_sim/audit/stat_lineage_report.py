from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

_REQUIRED_MANIFEST_KEYS = (
    "required_max_wave_stat_input_ids",
    "status_lists",
)
_REQUIRED_STATUS_KEYS = (
    "still_requires_wiring_up",
    "wired_up",
    "not_expected_to_be_wired_up",
)


def _expect_mapping(value: Any, *, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be a mapping")
    return value


def _expect_list(value: Any, *, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    return value


def load_manifest(path: Path) -> Mapping[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    manifest = _expect_mapping(payload, context="manifest")

    for key in _REQUIRED_MANIFEST_KEYS:
        if key not in manifest:
            raise ValueError(f"manifest missing required key: {key}")

    status_lists = _expect_mapping(manifest["status_lists"], context="status_lists")
    for stat_id, status in status_lists.items():
        status_mapping = _expect_mapping(status, context=f"status_lists[{stat_id}]")
        for key in _REQUIRED_STATUS_KEYS:
            if key not in status_mapping:
                raise ValueError(f"status_lists[{stat_id}] missing required key: {key}")
            _expect_list(status_mapping[key], context=f"status_lists[{stat_id}].{key}")

    _expect_list(manifest["required_max_wave_stat_input_ids"], context="required_max_wave_stat_input_ids")
    return manifest


def summarize_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    status_lists = _expect_mapping(manifest["status_lists"], context="status_lists")
    required_ids = _expect_list(
        manifest["required_max_wave_stat_input_ids"],
        context="required_max_wave_stat_input_ids",
    )

    missing_by_stat: dict[str, list[str]] = {}
    missing_by_contributor: dict[str, int] = {}

    for stat_id in sorted(status_lists):
        status = _expect_mapping(status_lists[stat_id], context=f"status_lists[{stat_id}]")
        missing = sorted(
            str(item)
            for item in _expect_list(
                status["still_requires_wiring_up"],
                context=f"status_lists[{stat_id}].still_requires_wiring_up",
            )
        )
        if not missing:
            continue
        missing_by_stat[str(stat_id)] = missing
        for contributor in missing:
            missing_by_contributor[contributor] = missing_by_contributor.get(contributor, 0) + 1

    required_max_wave_gaps = {
        stat_id: missing_by_stat[stat_id]
        for stat_id in sorted(str(item) for item in required_ids)
        if stat_id in missing_by_stat
    }

    return {
        "stats_total": len(status_lists),
        "stats_with_missing": len(missing_by_stat),
        "total_missing_pairs": sum(len(missing) for missing in missing_by_stat.values()),
        "missing_by_contributor": dict(sorted(missing_by_contributor.items())),
        "required_max_wave_gap_count": len(required_max_wave_gaps),
        "required_max_wave_gaps": required_max_wave_gaps,
        "missing_by_stat": missing_by_stat,
    }


def render_report(summary: Mapping[str, Any]) -> str:
    lines = [
        "Stat lineage wiring report",
        f"- stats_total: {summary['stats_total']}",
        f"- stats_with_missing: {summary['stats_with_missing']}",
        f"- total_missing_pairs: {summary['total_missing_pairs']}",
        f"- required_max_wave_gap_count: {summary['required_max_wave_gap_count']}",
        "- missing_by_contributor:",
    ]
    for contributor, count in summary["missing_by_contributor"].items():
        lines.append(f"  - {contributor}: {count}")

    lines.append("- required_max_wave_gaps:")
    for stat_id, missing in summary["required_max_wave_gaps"].items():
        lines.append(f"  - {stat_id}: {', '.join(missing)}")

    lines.append("- missing_by_stat:")
    for stat_id, missing in summary["missing_by_stat"].items():
        lines.append(f"  - {stat_id}: {', '.join(missing)}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize stat lineage gaps from out/stat_lineage_manifest_latest.json "
            "with fail-closed manifest-shape validation."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("out/stat_lineage_manifest_latest.json"),
        help="Path to stat lineage manifest JSON (default: out/stat_lineage_manifest_latest.json).",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path to write machine-readable summary JSON.",
    )
    args = parser.parse_args()

    summary = summarize_manifest(load_manifest(args.manifest))
    print(render_report(summary))

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
