from __future__ import annotations

import argparse
from pathlib import Path
import json
from typing import Any

from qe.module_reroll.ban_labs import ban_lab_capacities_from_account_state, build_ban_lab_wiring
from qe.module_reroll.domain import RerollMechanicsConfig
from qe.module_reroll.kb_loader import load_module_reroll_source_bundle
from qe.module_reroll.reports import validation_report


def write_json_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Experimental standalone module reroll mechanics CLI")
    parser.add_argument("--repo-root", default=".", type=Path)
    parser.add_argument("--output", type=Path, default=Path("out/experimental/module_reroll_validation_report.json"))
    parser.add_argument("--run-smoke", choices=["current_as"], default=None)
    parser.add_argument("--account-state", type=Path, default=None, help="Optional account_state.json payload used to resolve module effect-ban lab capacity.")
    parser.add_argument("--selected-bans", type=Path, default=None, help="Optional JSON mapping family names to selected banned effect names or ids.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    source_bundle = load_module_reroll_source_bundle(repo_root)
    mechanics = RerollMechanicsConfig(
        rarity_probabilities=source_bundle.rarity_probabilities,
        lock_costs=source_bundle.lock_costs,
    )
    counts = {family.value: len(specs) for family, specs in source_bundle.effect_specs.items()}
    selected_bans = {}
    if args.selected_bans is not None:
        selected_bans = json.loads(args.selected_bans.read_text())
    ban_lab_wiring = None
    if args.account_state is not None:
        account_state_path = (repo_root / args.account_state) if not args.account_state.is_absolute() else args.account_state
        account_state_payload = json.loads(account_state_path.read_text())
        capacities = ban_lab_capacities_from_account_state(account_state_payload, repo_root=repo_root)
        ban_lab_wiring = build_ban_lab_wiring(capacities, selected_bans, source_bundle.effect_specs)
    report = validation_report(counts, mechanics, ban_lab_wiring=ban_lab_wiring)
    report["input"] = {
        "smoke_fixture": args.run_smoke or "kb_validation",
        "account_state": str(args.account_state) if args.account_state is not None else None,
        "selected_bans": str(args.selected_bans) if args.selected_bans is not None else None,
    }
    write_json_report((repo_root / args.output) if not args.output.is_absolute() else args.output, report)
    print(f"wrote experimental module reroll validation report to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
