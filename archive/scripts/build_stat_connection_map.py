#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

KB_CONTRIBUTOR_MAPPINGS = Path("kb/kb/global-rules/contracts/contributor-mappings-full.yaml")


def build_connection_rows() -> list[dict[str, str]]:
    payload = yaml.safe_load(KB_CONTRIBUTOR_MAPPINGS.read_text(encoding="utf-8"))
    source_families = payload.get("source_families")
    if not isinstance(source_families, dict):
        raise RuntimeError("Invalid KB contributor mapping: source_families must be a mapping.")

    rows: list[dict[str, str]] = []
    for source_family, entries in sorted(source_families.items()):
        if not isinstance(entries, list):
            raise RuntimeError(f"Invalid entries for family={source_family!r}: expected list.")
        for entry in entries:
            if not isinstance(entry, dict):
                raise RuntimeError(f"Invalid mapping row for family={source_family!r}: expected mapping.")

            contributor_id = str(entry.get("contributor_id") or "").strip()
            destination_object_type = str(entry.get("destination_object_type") or "").strip()
            destination_id = str(entry.get("destination_id") or "").strip()
            resolver = str(entry.get("resolver") or "").strip()
            if contributor_id == "" or destination_object_type == "" or destination_id == "":
                raise RuntimeError(
                    f"Invalid mapping row for family={source_family!r}:"
                    " contributor_id, destination_object_type, destination_id are required."
                )

            rows.append(
                {
                    "source_family": str(source_family),
                    "contributor_id": contributor_id,
                    "destination_object_type": destination_object_type,
                    "destination_id": destination_id,
                    "resolver": resolver,
                }
            )

    rows.sort(
        key=lambda row: (
            row["destination_object_type"],
            row["destination_id"],
            row["source_family"],
            row["contributor_id"],
        )
    )
    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_family",
                "contributor_id",
                "destination_object_type",
                "destination_id",
                "resolver",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build consolidated KB stat connection map artifact.")
    parser.add_argument("--output", type=Path, default=Path("out/stat_connection_map.csv"))
    args = parser.parse_args()

    rows = build_connection_rows()
    write_csv(rows, args.output)
    print(
        {
            "source": str(KB_CONTRIBUTOR_MAPPINGS),
            "rows": len(rows),
            "output": str(args.output),
        }
    )


if __name__ == "__main__":
    main()
