from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class ComponentStatus:
    name: str
    status: str
    evidence: Sequence[str]
    tests: Sequence[str]
    known_gaps: Sequence[str]


def _format_cell(items: Iterable[str]) -> str:
    cleaned = [item.strip() for item in items if item.strip()]
    if not cleaned:
        return "—"
    return "<br>".join(cleaned)


def _components() -> list[ComponentStatus]:
    return [
        ComponentStatus(
            name="Ids parsing",
            status="implemented",
            evidence=[
                "`tower_sim/ids_parser.py`: `parse_ids`, section parsing",
                "`tower_sim/ids_state.py`: typed `IdsState`",
            ],
            tests=["`tests/test_ids_parser.py`"],
            known_gaps=[],
        ),
        ComponentStatus(
            name="DataLoader",
            status="partial",
            evidence=[
                "`tower_sim/sources.py`: `load_snapshot_bundle`, `load_ids_only_bundle`",
            ],
            tests=["`tests/test_sources.py`"],
            known_gaps=[
                "No spec-driven loader or snapshot selection wired into a run entrypoint.",
            ],
        ),
        ComponentStatus(
            name="Stat engine",
            status="partial",
            evidence=[
                "`tower_sim/stat_engine.py`: `StatEngine`, `StatInput`",
                "`tower_sim/stat_registry.py`: `default_registry`",
            ],
            tests=[
                "`tests/test_stat_engine.py`",
                "`tests/test_stat_engine_tier_rules.py`",
            ],
            known_gaps=[
                "Derived stat composition/DPS formulas are incomplete; see "
                "[Effective Paths mechanics comparison]"
                "(audit/effective_paths_mechanics_comparison.md#effective-paths-v50001-master-workbook).",
            ],
        ),
        ComponentStatus(
            name="Statbook builder",
            status="implemented",
            evidence=[
                "`tower_sim/statbook.py`: StatBook schema",
                "`tower_sim/statbook_builder.py`: `build_statbook`, `build_canonical_statbook`",
            ],
            tests=[
                "`tests/test_statbook_builder.py`",
                "`tests/test_statbook_reference_structure.py`",
            ],
            known_gaps=[],
        ),
        ComponentStatus(
            name="Workshop progression",
            status="partial",
            evidence=[
                "`tower_sim/workshop_progression.py`: `simulate_workshop_progression`",
            ],
            tests=["`tests/test_workshop_progression.py`"],
            known_gaps=[
                "Free Upgrade allocation policy is fail-closed; see "
                "[Workshop / WS+ / Free upgrades]"
                "(audit/effective_paths_mechanics_comparison.md#workshop--ws---free-upgrades).",
            ],
        ),
        ComponentStatus(
            name="Skip mapping",
            status="implemented",
            evidence=[
                "`tower_sim/wave_engine.py`: `SkipRamp`, `expected_skipped_waves`, `make_wave_state`",
            ],
            tests=["`tests/test_wave_engine.py`"],
            known_gaps=[],
        ),
        ComponentStatus(
            name="BC/heat",
            status="partial",
            evidence=[
                "`tower_sim/battle_conditions.py`: `BattleConditions`",
                "`tower_sim/tier_bc_loader.py`: `load_tier_battle_conditions`",
                "`tower_sim/tournament_bc_selection.py`: league BC enumeration",
            ],
            tests=[
                "`tests/test_battle_conditions_context.py`",
                "`tests/test_tier_battle_conditions.py`",
                "`tests/test_tier_bc_loader.py`",
                "`tests/test_tournament_bc_selection.py`",
            ],
            known_gaps=[
                "Heat curves are loaded from tables, but no end-to-end run integration.",
            ],
        ),
        ComponentStatus(
            name="Wave damage",
            status="partial",
            evidence=[
                "`tower_sim/enemies/wave_damage_strict.py`: strict wave damage library",
            ],
            tests=["`tests/test_imports.py`"],
            known_gaps=[
                "Only sparse anchor tables; full per-wave tables are not loaded.",
            ],
        ),
        ComponentStatus(
            name="Boss combat",
            status="stub",
            evidence=[
                "`tower_sim/combat/boss_engine.py`: fail-closed placeholder",
                "`tower_sim/combat/boss_survivability.py`: TTK/TTD resolution",
            ],
            tests=[
                "`tests/test_boss_engine.py`",
                "`tests/test_boss_survivability.py`",
            ],
            known_gaps=[
                "Boss combat mechanics (PC, thorns, regen, DR) are not implemented.",
            ],
        ),
        ComponentStatus(
            name="Evaluator",
            status="missing",
            evidence=[
                "No `MaxWaveEvaluator` implementation in `tower_sim/`.",
            ],
            tests=[],
            known_gaps=[
                "No deterministic Wmax evaluation pipeline exists.",
            ],
        ),
        ComponentStatus(
            name="CLI",
            status="missing",
            evidence=[
                "No `python -m tower_sim.run` entrypoint exists.",
            ],
            tests=[],
            known_gaps=[
                "Spec parsing/dispatch not implemented.",
            ],
        ),
        ComponentStatus(
            name="Validation harness",
            status="partial",
            evidence=[
                "`tower_sim/audit/repo_audit.py`: repo audit CLI",
                "`tower_sim/audit/stat_source_coverage.py`: stat source coverage",
                "`tower_sim/wiki/cache_audit.py`: wiki cache audit",
            ],
            tests=[
                "`tests/test_repo_audit.py`",
                "`tests/test_stat_source_coverage.py`",
                "`tests/test_cache_audit.py`",
            ],
            known_gaps=[
                "No validation harness against Harry’s reference sheets.",
            ],
        ),
    ]


def _critical_path() -> list[str]:
    return [
        "Define a run spec schema + parser for `python -m tower_sim.run --spec <fixture>`.",
        "Implement a deterministic `MaxWaveEvaluator` that wires IDS + snapshot inputs.",
        "Integrate per-wave stat composition (workshop progression + skip mapping).",
        "Wire battle conditions and heat selections into per-wave stats.",
        "Load authoritative per-wave enemy damage tables (replace strict anchors).",
        "Implement boss combat mechanics with authoritative formulas (PC/thorns/regen/DR).",
        "Compute wave outcomes deterministically and emit Wmax JSON.",
        "Add end-to-end validation harness vs reference sheets once available.",
    ]


def generate_report() -> str:
    rows = _components()
    lines = [
        "# Implementation Status Report",
        "",
        "Regenerate with:",
        "",
        "```bash",
        "python -m tower_sim.audit.status",
        "```",
        "",
        "## Component status table",
        "",
        "| Component | Status | Evidence | Tests | Known gaps |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.name,
                    row.status,
                    _format_cell(row.evidence),
                    _format_cell(row.tests),
                    _format_cell(row.known_gaps),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Critical path to a runnable MaxWaveEvaluator (deterministic Wmax JSON)",
            "",
        ]
    )
    for item in _critical_path():
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def write_report(path: Path) -> None:
    path.write_text(generate_report(), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the TowerSim implementation status report."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for the report (default: audit/implementation_status_report.md).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if the existing report differs from generated output.",
    )
    args = parser.parse_args(argv)

    repo_root = _resolve_repo_root()
    output_path = args.output or repo_root / "audit" / "implementation_status_report.md"
    content = generate_report()

    if args.check:
        if not output_path.exists():
            raise FileNotFoundError(output_path)
        existing = output_path.read_text(encoding="utf-8")
        return 0 if existing == content else 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
