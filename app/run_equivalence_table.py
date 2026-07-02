"""
app/run_equivalence_table.py -- Thin CLI for enemy-pressure equivalence tables.

Owns: argument parsing and rendering only.
Must not own: mechanic truth, account import parsing, or optimisation policy.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluators.equivalence import (  # noqa: E402
    EnemyCurve,
    SurfaceCalibration,
    build_equivalence_table,
    pivot_displayed_waves,
    rows_to_csv_text,
    rows_to_json_text,
)

DEFAULT_DAMAGE_LABELS = (
    "1N",
    "10N",
    "100N",
    "1D",
    "10D",
    "40D",
    "100D",
    "1aa",
    "10aa",
    "100aa",
    "1ab",
    "10ab",
    "100ab",
    "1ac",
)

DEFAULT_SURFACES = ("Tier 14", "Tier 15", "Tier 16", "Tier 17", "Legend")


def _parse_pct(value: str) -> float:
    raw = value.strip()
    if raw.endswith("%"):
        return float(raw[:-1]) / 100.0
    parsed = float(raw)
    return parsed / 100.0 if parsed > 1 else parsed


def _surface_map(raw: str) -> dict[str, float]:
    """Parse comma-separated Surface=value percentages."""
    if not raw:
        return {}
    output: dict[str, float] = {}
    for item in raw.split(","):
        if not item.strip():
            continue
        surface, value = item.split("=", 1)
        output[surface.strip()] = _parse_pct(value)
    return output


def _parse_legend_anchor(raw: str | None, curves: dict[str, EnemyCurve]) -> dict[str, SurfaceCalibration]:
    if not raw:
        return {}
    # Format: Legend=40D:550. Future surfaces can use the same format.
    calibrations: dict[str, SurfaceCalibration] = {}
    for item in raw.split(","):
        if not item.strip():
            continue
        surface, spec = item.split("=", 1)
        damage_label, wave_text = spec.split(":", 1)
        surface = surface.strip()
        if surface not in curves:
            raise ValueError(f"Cannot calibrate unknown surface {surface!r}")
        calibrations[surface] = SurfaceCalibration.from_anchor(
            surface=surface,
            curve=curves[surface],
            damage_label=damage_label.strip(),
            displayed_wave=float(wave_text),
            source="cli_anchor",
        )
    return calibrations


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate enemy-pressure equivalence tables.")
    parser.add_argument(
        "--health-table",
        type=Path,
        default=ROOT / "kb" / "enemies" / "tables" / "enemy-health-table.csv",
    )
    parser.add_argument(
        "--damage-table",
        type=Path,
        default=ROOT / "kb" / "enemies" / "tables" / "enemy-damage-table.csv",
    )
    parser.add_argument(
        "--axis",
        choices=("health", "damage"),
        default="health",
        help="health uses EHLS; damage uses EALS.",
    )
    parser.add_argument(
        "--surfaces",
        default=",".join(DEFAULT_SURFACES),
        help="Comma-separated table surfaces, e.g. 'Tier 14,Tier 15,Legend'.",
    )
    parser.add_argument(
        "--damage-labels",
        default=",".join(DEFAULT_DAMAGE_LABELS),
        help="Comma-separated compact damage labels.",
    )
    parser.add_argument(
        "--skip-chances",
        default="",
        help=(
            "Optional comma-separated fixed skip chances by surface, e.g. "
            "'Tier 15=44.88%,Legend=0'. Use EHLS for health axis and EALS for damage axis."
        ),
    )
    parser.add_argument(
        "--calibration-anchors",
        default="",
        help="Optional comma-separated Surface=DamageLabel:Wave anchors, e.g. 'Legend=40D:550'.",
    )
    parser.add_argument("--json", action="store_true", help="Emit detailed JSON rows instead of pivot CSV.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output path. Defaults to stdout.",
    )
    args = parser.parse_args()

    surfaces = [surface.strip() for surface in args.surfaces.split(",") if surface.strip()]
    damage_labels = [label.strip() for label in args.damage_labels.split(",") if label.strip()]
    table_path = args.health_table if args.axis == "health" else args.damage_table
    curves = {surface: EnemyCurve.from_wide_csv(table_path, surface) for surface in surfaces}
    skip_chances = _surface_map(args.skip_chances)
    calibrations = _parse_legend_anchor(args.calibration_anchors, curves)

    results = build_equivalence_table(
        damage_labels=damage_labels,
        curves=curves,
        axis=args.axis,
        skip_chances=skip_chances,
        calibrations=calibrations,
    )
    if args.json:
        text = rows_to_json_text([result.to_row() for result in results])
    else:
        text = rows_to_csv_text(pivot_displayed_waves(results))

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
