from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml

TOKEN_INVENTORY_PATH = Path("audit/effective_paths_formula_comparison.md")
TOKEN_SOURCE_MAP_PATH = Path("audit/token_source_map.yaml")
TOKEN_SOURCE_REPORT_PATH = Path("audit/token_source_report.md")


@dataclass(frozen=True)
class TokenOccurrence:
    workbook: str
    sheet: str


@dataclass(frozen=True)
class TokenSource:
    token: str
    gate: str
    source_type: str
    source_path: str
    source_locator: str
    notes: str


def parse_token_inventory(markdown_path: Path) -> Dict[str, List[TokenOccurrence]]:
    if not markdown_path.exists():
        raise FileNotFoundError(f"Token inventory markdown not found: {markdown_path}")

    workbook: str | None = None
    sheet: str | None = None
    occurrences: Dict[str, List[TokenOccurrence]] = defaultdict(list)
    for line in markdown_path.read_text().splitlines():
        if line.startswith("## "):
            workbook = line[3:].strip()
            sheet = None
            continue
        if line.startswith("### Sheet: "):
            sheet = line.split(":", 1)[1].strip()
            continue
        token_match = _match_token_line(line)
        if token_match:
            if workbook is None or sheet is None:
                raise ValueError(
                    f"Token {token_match} found without workbook/sheet context."
                )
            occurrences[token_match].append(
                TokenOccurrence(workbook=workbook, sheet=sheet)
            )

    if not occurrences:
        raise ValueError(
            "No tokens found in token inventory markdown; extraction failed."
        )

    return occurrences


def _match_token_line(line: str) -> str | None:
    line = line.strip()
    if not line.startswith("- `"):
        return None
    end = line.find("`", 3)
    if end == -1:
        return None
    token = line[3:end]
    if not token:
        return None
    return token


def load_token_sources(yaml_path: Path) -> Dict[str, List[TokenSource]]:
    if not yaml_path.exists():
        raise FileNotFoundError(f"Token source map not found: {yaml_path}")

    data = yaml.safe_load(yaml_path.read_text())
    if not isinstance(data, list):
        raise ValueError("Token source map must be a list of mappings.")

    sources: Dict[str, List[TokenSource]] = defaultdict(list)
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError("Token source map entries must be mappings.")
        token = entry.get("token")
        if not token:
            raise ValueError("Token source map entry missing token.")
        sources[token].append(
            TokenSource(
                token=token,
                gate=entry.get("gate", ""),
                source_type=entry.get("source_type", ""),
                source_path=entry.get("source_path", ""),
                source_locator=entry.get("source_locator", ""),
                notes=entry.get("notes", ""),
            )
        )
    return sources


def find_conflicts(
    sources: Dict[str, List[TokenSource]],
) -> Dict[str, List[TokenSource]]:
    conflicts: Dict[str, List[TokenSource]] = {}
    for token, entries in sources.items():
        if len(entries) <= 1:
            continue
        unique = {
            (
                entry.source_type,
                entry.source_path,
                entry.source_locator,
                entry.gate,
            )
            for entry in entries
        }
        if len(unique) > 1:
            conflicts[token] = entries
    return conflicts


def validate_sources(
    token_occurrences: Dict[str, List[TokenOccurrence]],
    sources: Dict[str, List[TokenSource]],
) -> Tuple[List[str], List[str], Dict[str, List[TokenSource]]]:
    missing = [token for token in sorted(token_occurrences) if token not in sources]
    unmapped = []
    for token, entries in sources.items():
        for entry in entries:
            if entry.source_type == "unknown":
                unmapped.append(token)
                break
    conflicts = find_conflicts(sources)
    return missing, sorted(set(unmapped)), conflicts


def gate_a_unmapped(
    token_occurrences: Dict[str, List[TokenOccurrence]],
    sources: Dict[str, List[TokenSource]],
) -> List[str]:
    gate_a = set()
    for token in token_occurrences:
        if token in sources:
            for entry in sources[token]:
                if entry.gate == "A":
                    gate_a.add(token)
                    break
    unmapped = []
    for token in sorted(gate_a):
        entries = sources.get(token, [])
        if not entries:
            unmapped.append(token)
            continue
        if any(entry.source_type == "unknown" for entry in entries):
            unmapped.append(token)
    return unmapped


def build_report(
    token_occurrences: Dict[str, List[TokenOccurrence]],
    sources: Dict[str, List[TokenSource]],
    missing: Iterable[str],
    unmapped: Iterable[str],
    gate_a_unmapped_tokens: Iterable[str],
) -> str:
    missing_set = set(missing)
    unmapped_set = set(unmapped)
    total_tokens = len(token_occurrences)
    mapped_tokens = total_tokens - len(missing_set) - len(unmapped_set)
    gate_a_unmapped_set = set(gate_a_unmapped_tokens)

    grouped = group_by_subsystem(sorted(missing_set | unmapped_set))

    lines = [
        "# Token Source Report",
        "",
        "## Summary",
        f"- Total tokens: {total_tokens}",
        f"- Mapped tokens: {mapped_tokens}",
        f"- Unmapped tokens: {len(missing_set | unmapped_set)}",
        f"- Gate A unmapped tokens: {len(gate_a_unmapped_set)}",
        "",
        "## Unmapped tokens by suspected subsystem",
        "",
        "| Subsystem | Tokens |",
        "| --- | --- |",
    ]

    if not grouped:
        lines.append("| (none) | (none) |")
    else:
        for subsystem in sorted(grouped):
            token_list = ", ".join(grouped[subsystem])
            lines.append(f"| {subsystem} | {token_list} |")

    lines.append("")
    return "\n".join(lines)


def group_by_subsystem(tokens: Iterable[str]) -> Dict[str, List[str]]:
    grouped: Dict[str, List[str]] = defaultdict(list)
    for token in tokens:
        grouped[guess_subsystem(token)].append(token)
    for tokens_list in grouped.values():
        tokens_list.sort()
    return grouped


def guess_subsystem(token: str) -> str:
    if token.startswith("DVT_BOT"):
        return "Bots"
    if token.startswith("DVT_GAR") or token.startswith("DVT_GUARDIAN"):
        return "Guardians"
    if token.startswith("IDS_"):
        return "IDS / Inventory"
    if token.startswith("MOD") or token.startswith("MODSTAT"):
        return "Modules"
    if token.startswith("LAB") or token.startswith("LABCOST") or token.startswith(
        "LABDURATION"
    ):
        return "Labs"
    if token.startswith("WS") or token.startswith("WSP"):
        return "Workshop"
    if token.startswith("UW") or token.startswith("UWDMG") or token.startswith(
        "STAT_UW"
    ):
        return "Ultimate Weapons"
    if token.startswith("AUW"):
        return "Ultimate Weapons"
    if token.startswith("EP"):
        return "Effective Paths"
    if token.startswith("CARD"):
        return "Cards"
    if token in {"EALS", "EHLS", "ELS"}:
        return "Wave Mapping"
    if token == "TIER":
        return "Tier/BC"
    return "Utilities/Other"


def write_report(report_path: Path, report_text: str) -> None:
    report_path.write_text(report_text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate token source mappings.")
    parser.add_argument(
        "--inventory",
        type=Path,
        default=TOKEN_INVENTORY_PATH,
        help="Path to token inventory markdown.",
    )
    parser.add_argument(
        "--source-map",
        type=Path,
        default=TOKEN_SOURCE_MAP_PATH,
        help="Path to token source map YAML.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=TOKEN_SOURCE_REPORT_PATH,
        help="Path to write the token source report.",
    )
    args = parser.parse_args()

    token_occurrences = parse_token_inventory(args.inventory)
    sources = load_token_sources(args.source_map)
    missing, unmapped, conflicts = validate_sources(token_occurrences, sources)
    gate_a_unmapped_tokens = gate_a_unmapped(token_occurrences, sources)

    report_text = build_report(
        token_occurrences,
        sources,
        missing,
        unmapped,
        gate_a_unmapped_tokens,
    )
    write_report(args.report, report_text)

    exit_code = 0
    if missing or unmapped or gate_a_unmapped_tokens:
        exit_code = 1
    if conflicts:
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
