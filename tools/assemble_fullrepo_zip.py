#!/usr/bin/env python3
"""Assemble the split TowerSim step1 FULLREPO archive into a single zip.

This script is deterministic and fail-closed: if the assembled file does not
contain a ZIP end-of-central-directory record, it raises an error.
"""
from __future__ import annotations

import argparse
from pathlib import Path

EOCD_SIGNATURE = b"PK\x05\x06"


def find_parts(parts_dir: Path, prefix: str) -> list[Path]:
    return sorted(parts_dir.glob(f"{prefix}.part*"))


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

    write_combined(parts, args.output)

    if not has_eocd(args.output):
        raise SystemExit(
            "Combined archive is missing the ZIP end-of-central-directory record. "
            "The split set is likely incomplete."
        )

    print(f"Wrote combined archive to {args.output}")


if __name__ == "__main__":
    main()
