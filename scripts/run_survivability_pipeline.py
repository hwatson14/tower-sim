from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Optional

from tower_sim.engines.survivability_pipeline import (
    SurvivabilityPipelineError,
    build_survivability_report,
)
from tower_sim.loaders.ids_parser import parse_ids
from tower_sim.run.spec_loader import load_problem_spec


def _parse_module_overrides(values: list[str]) -> Dict[str, Dict[str, Optional[str]]]:
    overrides: Dict[str, Dict[str, Optional[str]]] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid override {item!r}; expected SLOT=NAME.")
        slot, name = item.split("=", 1)
        slot = slot.strip().title()
        name = name.strip()
        overrides.setdefault(slot, {})["primary"] = name if name else None
    return overrides


def _parse_assist_overrides(values: list[str]) -> Dict[str, Dict[str, Optional[str]]]:
    overrides: Dict[str, Dict[str, Optional[str]]] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"Invalid override {item!r}; expected SLOT=NAME.")
        slot, name = item.split("=", 1)
        slot = slot.strip().title()
        name = name.strip()
        overrides.setdefault(slot, {})["assist"] = name if name else None
    return overrides


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run survivability pipeline and emit JSON snapshots."
    )
    parser.add_argument(
        "--ids",
        type=Path,
        default=None,
        help="Path to _IDS.csv (defaults to repo fixture resolution).",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=Path("tests/fixtures/specs/sample_spec.json"),
        help="Problem spec JSON/YAML file.",
    )
    parser.add_argument(
        "--module-context",
        default="Testing",
        choices=["Testing", "Farming", "Tourney"],
        help="Module context to select loadout.",
    )
    parser.add_argument(
        "--module-primary",
        action="append",
        default=[],
        metavar="SLOT=NAME",
        help="Override primary module for a slot (e.g. Armor=Sharp Fortitude).",
    )
    parser.add_argument(
        "--module-assist",
        action="append",
        default=[],
        metavar="SLOT=NAME",
        help="Override assist module for a slot (e.g. Armor=Restorative Bonus).",
    )
    parser.add_argument(
        "--card",
        action="append",
        default=[],
        metavar="NAME",
        help="Explicitly include a card by name.",
    )
    parser.add_argument(
        "--allow-provisional",
        action="store_true",
        help="Allow provisional EP-backed ladders that lack tables.",
    )
    args = parser.parse_args()

    ids_state = parse_ids(args.ids)
    spec = load_problem_spec(args.spec)

    module_overrides = _parse_module_overrides(args.module_primary)
    assist_overrides = _parse_assist_overrides(args.module_assist)
    for slot, assist_data in assist_overrides.items():
        module_overrides.setdefault(slot, {}).update(assist_data)

    try:
        report = build_survivability_report(
            ids_state,
            spec,
            module_context=args.module_context,
            module_overrides=module_overrides or None,
            selected_cards=args.card or None,
            allow_provisional=args.allow_provisional,
        )
    except SurvivabilityPipelineError as exc:
        payload = {"error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        raise SystemExit(1) from exc

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
