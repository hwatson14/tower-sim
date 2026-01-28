"""Demo: tournament BC scenario enumeration + signal application.

This is a *debug / validation tool*.

It does NOT simulate combat. It only proves that we can:
  (1) ingest per-wave tournament BC magnitudes from Player & Stuff
  (2) enumerate deterministic BC sets (not all present together)
  (3) materialize BC signals into a state dict, fail-closed.

Run:
  python -m tools.demo_tournament_bc_scenarios --league gold --wave 200
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from adapter.tournament_bc_apply import build_tournament_scenarios, apply_tournament_scenario_to_state


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--league", required=True)
    ap.add_argument("--wave", required=True, type=int)
    ap.add_argument("--max", dest="max_variants", type=int, default=25)
    args = ap.parse_args()

    data_path = Path(__file__).resolve().parents[1] / "data" / "tournament_bc_magnitudes_from_player_and_stuff.csv"
    df = pd.read_csv(data_path)

    scenarios = build_tournament_scenarios(
        league=args.league,
        wave=args.wave,
        bc_magnitudes=df,
        max_variants=args.max_variants,
    )

    print(f"league={args.league} wave={args.wave} variants={len(scenarios)}")
    base_state = {"coins": 0.0, "cells": 0.0}

    # Print first N variants
    for i, sc in enumerate(scenarios[: args.max_variants], start=1):
        st = apply_tournament_scenario_to_state(state=base_state, scenario=sc, bc_magnitudes=df)
        bc_block = st.get("battle_conditions", {})
        print(f"\n#{i} weight={sc.weight:.6f} bcs={list(sc.bc_ids)}")
        print(json.dumps(bc_block, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
