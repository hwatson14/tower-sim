"""Regenerate IDS ABI lock artifacts from a wide _IDS.csv export.

Why this exists:
  - adapter/account.py fail-closes if the wide IDS header row drifts from the
    previously locked header in refs/ids_abi_lock/IDS_ABI_LOCKED_RAW_v1.csv.
  - This script updates the lock files deterministically from a provided IDS.

Usage:
  python tools/update_ids_abi_lock.py --ids refs/_IDS.csv

Outputs (overwritten):
  refs/ids_abi_lock/IDS_ABI_LOCKED_RAW_v1.csv
  refs/ids_abi_lock/IDS_ABI_LOCKED_CANON_v1.csv

Notes:
  - This is intentionally conservative: it only updates the header lock, not
    any value snapshots.
  - Keep this change under version control so drift is explicit and reviewable.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def _read_first_row_csv(path: Path) -> list[str]:
    # Wide IDS exports are comma-separated and may contain empty cells.
    # We only need the first row as-is.
    raw = path.read_text(encoding="utf-8").splitlines()
    if not raw:
        raise SystemExit(f"Empty IDS file: {path}")
    return raw[0].split(",")


def main() -> int:
    ap = argparse.ArgumentParser(description="Update IDS ABI lock header from _IDS.csv")
    ap.add_argument("--ids", required=True, help="Path to wide _IDS.csv")
    ap.add_argument(
        "--out_dir",
        default="refs/ids_abi_lock",
        help="Output directory containing IDS_ABI_LOCKED_* files",
    )
    args = ap.parse_args()

    ids_p = Path(args.ids)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    header = _read_first_row_csv(ids_p)
    raw_lock = out_dir / "IDS_ABI_LOCKED_RAW_v1.csv"
    canon_lock = out_dir / "IDS_ABI_LOCKED_CANON_v1.csv"

    # RAW lock: preserve column count and empties.
    raw_lock.write_text(",".join(header) + "\n", encoding="utf-8")

    # CANON lock: strip purely empty trailing columns to reduce spurious drift.
    canon = list(header)
    while canon and canon[-1] == "":
        canon.pop()
    canon_lock.write_text(",".join(canon) + "\n", encoding="utf-8")

    print(f"Updated: {raw_lock}")
    print(f"Updated: {canon_lock}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
