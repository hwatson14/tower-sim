from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

_REQUIRED_MANIFEST_KEYS = (
    "required_max_wave_stat_input_ids",
)
_REQUIRED_STATUS_KEYS = (
    "still_requires_wiring_up",
    "wired_up",
    "not_expected_to_be_wired_up",
)

_FOCUS_CONTRIBUTORS = (
    "workshop",
    "relic",
    "card",
    "lab",
    "module",
    "enhancement",
    "bot",
    "perk",
    "bc",
    "uw",
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

    _status_lists(manifest)

    _expect_list(manifest["required_max_wave_stat_input_ids"], context="required_max_wave_stat_input_ids")
    return manifest


def _status_lists(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    if "status_lists" in manifest:
        status_lists = _expect_mapping(manifest["status_lists"], context="status_lists")
        for stat_id, status in status_lists.items():
            status_mapping = _expect_mapping(status, context=f"status_lists[{stat_id}]")
            for key in _REQUIRED_STATUS_KEYS:
                if key not in status_mapping:
                    raise ValueError(f"status_lists[{stat_id}] missing required key: {key}")
                _expect_list(status_mapping[key], context=f"status_lists[{stat_id}].{key}")
        return status_lists

    if manifest.get("schema") != "lineage_manifest.v1":
        raise ValueError("manifest missing required key: status_lists")

    stats = _expect_mapping(manifest.get("stats"), context="stats")
    normalized: dict[str, dict[str, list[str]]] = {}
    for stat_id, entries_raw in stats.items():
        entries = _expect_list(entries_raw, context=f"stats[{stat_id}]")
        wired: list[str] = []
        missing: list[str] = []
        not_expected: list[str] = []
        for item in entries:
            entry = _expect_mapping(item, context=f"stats[{stat_id}][]")
            contributor = str(entry.get("contributor"))
            reaches = bool(entry.get("reaches_stat_input"))
            exclusion_reason = str(entry.get("exclusion_reason")) if entry.get("exclusion_reason") else ""
            if reaches:
                wired.append(contributor)
            elif exclusion_reason == "excluded:not_wired_to_canonical_stat_input":
                missing.append(contributor)
            else:
                not_expected.append(contributor)
        normalized[str(stat_id)] = {
            "wired_up": sorted(wired),
            "not_expected_to_be_wired_up": sorted(not_expected),
            "still_requires_wiring_up": sorted(missing),
        }
    return normalized


def summarize_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    status_lists = _status_lists(manifest)
    required_ids = _expect_list(
        manifest["required_max_wave_stat_input_ids"],
        context="required_max_wave_stat_input_ids",
    )
    required_id_set = {str(item) for item in required_ids}

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

    contributor_totals = _summarize_contributor_totals(status_lists)

    return {
        "stats_total": len(status_lists),
        "stats_with_missing": len(missing_by_stat),
        "total_missing_pairs": sum(len(missing) for missing in missing_by_stat.values()),
        "missing_by_contributor": dict(sorted(missing_by_contributor.items())),
        "required_max_wave_gap_count": len(required_max_wave_gaps),
        "required_max_wave_gaps": required_max_wave_gaps,
        "missing_by_stat": missing_by_stat,
        "contributor_totals": contributor_totals,
        "focus_section_status": _focus_section_status(contributor_totals),
        "full_table": _build_full_table(status_lists, required_id_set=required_id_set),
    }


def _build_full_table(
    status_lists: Mapping[str, Any], *, required_id_set: set[str]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stat_id in sorted(status_lists):
        status = _expect_mapping(status_lists[stat_id], context=f"status_lists[{stat_id}]")
        wired = {str(item) for item in _expect_list(status["wired_up"], context=f"status_lists[{stat_id}].wired_up")}
        not_expected = {
            str(item)
            for item in _expect_list(
                status["not_expected_to_be_wired_up"],
                context=f"status_lists[{stat_id}].not_expected_to_be_wired_up",
            )
        }
        missing = {
            str(item)
            for item in _expect_list(
                status["still_requires_wiring_up"],
                context=f"status_lists[{stat_id}].still_requires_wiring_up",
            )
        }
        contributor_status: dict[str, str] = {}
        for contributor in _FOCUS_CONTRIBUTORS:
            if contributor in wired:
                contributor_status[contributor] = "wired"
            elif contributor in not_expected:
                contributor_status[contributor] = "not_expected"
            elif contributor in missing:
                contributor_status[contributor] = "missing"
            else:
                contributor_status[contributor] = "untracked"
        rows.append(
            {
                "stat_id": stat_id,
                "required_max_wave": stat_id in required_id_set,
                "contributors": contributor_status,
            }
        )
    return rows


def _summarize_contributor_totals(status_lists: Mapping[str, Any]) -> dict[str, dict[str, int | str]]:
    totals: dict[str, dict[str, int | str]] = {}
    for status in status_lists.values():
        status_mapping = _expect_mapping(status, context="status")
        for contributor in _expect_list(status_mapping["wired_up"], context="status.wired_up"):
            bucket = totals.setdefault(str(contributor), {"wired_pairs": 0, "missing_pairs": 0, "not_expected_pairs": 0})
            bucket["wired_pairs"] = int(bucket["wired_pairs"]) + 1
        for contributor in _expect_list(
            status_mapping["still_requires_wiring_up"], context="status.still_requires_wiring_up"
        ):
            bucket = totals.setdefault(str(contributor), {"wired_pairs": 0, "missing_pairs": 0, "not_expected_pairs": 0})
            bucket["missing_pairs"] = int(bucket["missing_pairs"]) + 1
        for contributor in _expect_list(
            status_mapping["not_expected_to_be_wired_up"], context="status.not_expected_to_be_wired_up"
        ):
            bucket = totals.setdefault(str(contributor), {"wired_pairs": 0, "missing_pairs": 0, "not_expected_pairs": 0})
            bucket["not_expected_pairs"] = int(bucket["not_expected_pairs"]) + 1

    normalized: dict[str, dict[str, int | str]] = {}
    for contributor, counts in sorted(totals.items()):
        wired = int(counts["wired_pairs"])
        missing = int(counts["missing_pairs"])
        not_expected = int(counts["not_expected_pairs"])
        if missing == 0 and wired > 0:
            status = "complete"
        elif missing > 0 and wired > 0:
            status = "partial"
        elif missing > 0 and wired == 0:
            status = "not_wired"
        else:
            status = "excluded"
        normalized[contributor] = {
            "wired_pairs": wired,
            "missing_pairs": missing,
            "not_expected_pairs": not_expected,
            "status": status,
        }
    return normalized


def _focus_section_status(contributor_totals: Mapping[str, Mapping[str, int | str]]) -> dict[str, dict[str, int | str]]:
    result: dict[str, dict[str, int | str]] = {}
    for contributor in _FOCUS_CONTRIBUTORS:
        if contributor in contributor_totals:
            result[contributor] = dict(contributor_totals[contributor])
            continue
        result[contributor] = {
            "wired_pairs": 0,
            "missing_pairs": 0,
            "not_expected_pairs": 0,
            "status": "not_tracked_in_lineage_contract",
        }
    return result


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

    lines.append("- focus_section_status:")
    for section, details in summary["focus_section_status"].items():
        lines.append(
            "  - "
            + f"{section}: status={details['status']}, wired_pairs={details['wired_pairs']}, "
            + f"missing_pairs={details['missing_pairs']}, not_expected_pairs={details['not_expected_pairs']}"
        )

    lines.append(f"- full_table_rows: {len(summary['full_table'])}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize stat lineage gaps from out/lineage_manifest_latest.json "
            "with fail-closed manifest-shape validation."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("out/lineage_manifest_latest.json"),
        help="Path to stat lineage manifest JSON (default: out/lineage_manifest_latest.json).",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path to write machine-readable summary JSON.",
    )
    parser.add_argument(
        "--full-table-out",
        type=Path,
        help="Optional path to write full per-stat contributor status table JSON.",
    )
    args = parser.parse_args()

    summary = summarize_manifest(load_manifest(args.manifest))
    print(render_report(summary))

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if args.full_table_out is not None:
        args.full_table_out.parent.mkdir(parents=True, exist_ok=True)
        args.full_table_out.write_text(
            json.dumps(summary["full_table"], indent=2, sort_keys=True),
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
