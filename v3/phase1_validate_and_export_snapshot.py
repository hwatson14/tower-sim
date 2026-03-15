from __future__ import annotations

import argparse
import json
from pathlib import Path
from v3.account_snapshot_compiler import compile_account_snapshot, snapshot_as_dict
from v3.ids_parser import SECTION_SPECS, parse_ids
from v3.kb_access import load_yaml

_IDS_ROUTING_IN_KB = "kb/global-rules/contracts/ids-section-routing.yaml"

# Explicit mapping between IDS routing contract names and parser section names.
_KB_TO_PARSER_SECTION = {
    "Labs": "Labs",
    "WS": "WS",
    "Enhancements": "WS+",
    "Ultimate Weapons (UWs)": "UWs",
    "Cards": "Cards",
    "Relics": "Relics",
    "Vault": "Vault",
    "Bots": "Bots",
    "Themes & Songs": "Themes & Songs",
    "Modules": "Modules",
    "Guardians": "Guardians",
    "Player & Stuff": "Player & Stuff",
}


def _load_kb_ids_sections() -> list[str]:
    doc = load_yaml(_IDS_ROUTING_IN_KB)
    sections = doc.get("sections", {})
    if not isinstance(sections, dict) or not sections:
        raise ValueError("KB ids-section-routing contract missing sections mapping.")
    return list(sections.keys())


def _validate_parser_against_kb() -> None:
    kb_sections = _load_kb_ids_sections()
    parser_sections = {spec.name for spec in SECTION_SPECS}
    expected_parser_sections = {
        _KB_TO_PARSER_SECTION[name] for name in kb_sections if name in _KB_TO_PARSER_SECTION
    }

    missing_map = [name for name in kb_sections if name not in _KB_TO_PARSER_SECTION]
    if missing_map:
        raise ValueError(
            "Missing KB→parser section mapping(s): " + ", ".join(sorted(missing_map))
        )

    if parser_sections != expected_parser_sections:
        raise ValueError(
            "Parser section set drift vs canonical KB routing contract. "
            f"parser_only={sorted(parser_sections - expected_parser_sections)}; "
            f"kb_only={sorted(expected_parser_sections - parser_sections)}"
        )


def run(ids_csv: Path, output_json: Path) -> None:
    _validate_parser_against_kb()
    ids_raw = parse_ids(ids_csv)
    snapshot = compile_account_snapshot(ids_raw)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(snapshot_as_dict(snapshot), indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate v3 Phase-1 IDS parser/compiler against extracted canonical KB and "
            "export full account snapshot JSON."
        )
    )
    parser.add_argument("--ids", type=Path, required=True, help="Path to _IDS.csv input.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("v3/account_snapshot_full.json"),
        help="Output JSON path.",
    )
    args = parser.parse_args()
    run(args.ids, args.out)


if __name__ == "__main__":
    main()
