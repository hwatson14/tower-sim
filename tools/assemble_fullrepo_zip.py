#!/usr/bin/env python3
"""Assemble the split TowerSim step1 FULLREPO archive into a single zip.

This script is deterministic and fail-closed: if the assembled file does not
contain a ZIP end-of-central-directory record, it raises an error.
"""
from __future__ import annotations

import argparse
from pathlib import Path

EOCD_SIGNATURE = b"PK\x05\x06"
PART_PREFIX = ".part"


def _parse_part_index(path: Path, prefix: str) -> int:
    name = path.name
    expected_prefix = f"{prefix}{PART_PREFIX}"
    if not name.startswith(expected_prefix):
        raise SystemExit(f"Unexpected part filename: {name}")
    suffix = name[len(expected_prefix) :]
    if not suffix.isdigit():
        raise SystemExit(
            f"Part filename suffix must be digits after '{expected_prefix}': {name}"
        )
    return int(suffix)


def find_parts(parts_dir: Path, prefix: str) -> list[Path]:
    parts = list(parts_dir.glob(f"{prefix}{PART_PREFIX}*"))
    indexed = sorted(((_parse_part_index(part, prefix), part) for part in parts))
    return [part for _, part in indexed]


def validate_part_sequence(parts: list[Path], prefix: str) -> None:
    indexes = [_parse_part_index(part, prefix) for part in parts]
    if not indexes:
        return
    min_index = min(indexes)
    max_index = max(indexes)
    expected = set(range(min_index, max_index + 1))
    missing = sorted(expected - set(indexes))
    if min_index != 0:
        raise SystemExit(
            f"Part sequence must start at 0; found minimum index {min_index}."
        )
    if missing:
        raise SystemExit(f"Missing part indexes: {missing}")


def write_combined(parts: list[Path], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as output_file:
        for part in parts:
            output_file.write(part.read_bytes())


def has_eocd(path: Path, max_scan: int = 66_000) -> bool:
    size = path.stat().st_size
    read_size = min(size, max_scan)
    with path.open("rb") as handle:
        handle.seek(size - read_size)
        tail = handle.read(read_size)
    return EOCD_SIGNATURE in tail


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble split FULLREPO parts into a single zip.",
    )
    parser.add_argument(
        "--parts-dir",
        type=Path,
        default=Path("reference"),
        help="Directory containing the split .part files.",
    )
    parser.add_argument(
        "--prefix",
        default="tower-sim-step1_FULLREPO",
        help="Prefix used for the split parts.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reference/tower-sim-step1_FULLREPO.zip"),
        help="Output path for the combined zip file.",
    )
    args = parser.parse_args()

    parts = find_parts(args.parts_dir, args.prefix)
    if not parts:
        raise SystemExit(
            f"No parts found in {args.parts_dir} for prefix '{args.prefix}'."
        )

    validate_part_sequence(parts, args.prefix)
    write_combined(parts, args.output)

    if not has_eocd(args.output):
        raise SystemExit(
            "Combined archive is missing the ZIP end-of-central-directory record. "
            "The split set is likely incomplete or corrupted."
        )

    print(f"Wrote combined archive to {args.output} from {len(parts)} parts.")


if __name__ == "__main__":
    main()
