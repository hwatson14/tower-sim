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
                "`tower_sim/loaders/ids_parser.py`: `parse_ids`, section parsing",
                "`tower_sim/util/ids_raw.py`: raw `_IDS.csv` ingest",
            ],
            tests=["`tests/test_ids_parser.py`"],
            known_gaps=[],
        ),
        ComponentStatus(
            name="DataLoader",
            status="implemented",
            evidence=[
                "`tower_sim/loaders/sources.py`: `load_snapshot_bundle`, `load_ids_only_bundle`",
                "`tower_sim/loaders/account_snapshot_loader.py`: snapshot JSON ingest",
                "`tower_sim/loaders/account_snapshot_compiler.py`: preset-aware account snapshot compilation",
            ],
            tests=[
                "`tests/test_sources.py`",
                "`tests/test_account_snapshot_compiler.py`",
            ],
            known_gaps=[
                "Remote snapshot fetch/pull is not implemented; loader is local-file based.",
            ],
        ),
        ComponentStatus(
            name="Stat engine",
            status="partial",
            evidence=[
                "`tower_sim/engines/stat_engine.py`: `StatEngine`, `StatInput`",
                "`tower_sim/registry/stat_registry.py`: `default_registry`",
                "`tower_sim/engines/stat_snapshots.py`: at-wave snapshot composition",
            ],
            tests=[
                "`tests/test_stat_engine.py`",
                "`tests/test_stat_engine_tier_rules.py`",
                "`tests/test_stat_snapshots.py`",
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
                "`tower_sim/util/statbook.py`: StatBook schema",
                "`tower_sim/engines/statbook_builder.py`: `build_statbook`, `build_canonical_statbook`",
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
                "`tower_sim/engines/workshop_progression.py`: `simulate_workshop_progression`",
                "`tower_sim/engines/free_upgrades.py`: deterministic expected free-upgrade model",
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
                "`tower_sim/engines/wave_engine.py`: `SkipRamp`, `expected_skipped_waves`, `make_wave_state`",
            ],
            tests=["`tests/test_wave_engine.py`"],
            known_gaps=[],
        ),
        ComponentStatus(
            name="BC/heat",
            status="partial",
            evidence=[
                "`tower_sim/engines/battle_conditions.py`: `BattleConditions`",
                "`tower_sim/loaders/tier_bc_loader.py`: tier BC table loading",
                "`tower_sim/loaders/bc_heat_loader.py`: tournament heat lookup",
                "`tower_sim/loaders/tournament_bc_selection.py`: league BC enumeration",
            ],
            tests=[
                "`tests/test_battle_conditions_context.py`",
                "`tests/test_tier_bc_loader.py`",
                "`tests/test_bc_heat_loader.py`",
                "`tests/test_tournament_bc_selection.py`",
            ],
            known_gaps=[
                "Unsupported BC families intentionally fail closed (`SUPPORTED_BC` allowlist).",
            ],
        ),
        ComponentStatus(
            name="Wave damage",
            status="implemented",
            evidence=[
                "`tower_sim/libs/wave_damage_strict.py`: strict enemy HP/damage tables with log-linear interpolation",
            ],
            tests=["`tests/test_wave_damage_strict.py`"],
            known_gaps=[
                "Only canonical HP/damage are represented; non-boss combat mechanics remain separate work.",
            ],
        ),
        ComponentStatus(
            name="Boss combat",
            status="implemented",
            evidence=[
                "`tower_sim/engines/combat/boss_engine.py`: deterministic PC/thorns/regen/DR core",
                "`tower_sim/engines/combat/boss_survivability.py`: TTK/TTD resolution",
                "`tower_sim/engines/combat/combat_engine.py`: survivability integration",
            ],
            tests=[
                "`tests/test_boss_engine.py`",
                "`tests/test_boss_survivability.py`",
                "`tests/test_combat_engine.py`",
            ],
            known_gaps=[
                "Model scope is boss survivability for v1; nonboss combat loop remains out of scope.",
            ],
        ),
        ComponentStatus(
            name="Evaluator",
            status="implemented",
            evidence=[
                "`tower_sim/evaluators/max_wave.py`: deterministic `MaxWaveEvaluator`",
                "`tower_sim/evaluators/max_wave_report.py`: report-friendly output adapters",
            ],
            tests=[
                "`tests/test_max_wave_v1_contract.py`",
                "`tests/test_max_wave_observability.py`",
                "`tests/test_run_api.py`",
            ],
            known_gaps=[
                "Economy objectives are deferred; v1 focuses on deterministic `MAX_WAVE`.",
            ],
        ),
        ComponentStatus(
            name="CLI",
            status="partial",
            evidence=[
                "`tower_sim/run/runner.py`: fixture runner CLI entrypoint",
                "`tower_sim/run/api.py`: allowlisted deterministic task dispatcher",
            ],
            tests=[
                "`tests/test_run_runner.py`",
                "`tests/test_run_api.py`",
                "`tests/test_run_context.py`",
            ],
            known_gaps=[
                "Runner CLI currently targets repo fixture defaults; user-facing CLI ergonomics are limited.",
            ],
        ),
        ComponentStatus(
            name="Validation harness",
            status="partial",
            evidence=[
                "`tower_sim/audit/repo_audit.py`: repo audit CLI",
                "`tower_sim/audit/stat_source_coverage.py`: stat source coverage",
                "`tower_sim/evaluators/max_wave_report.py`: evaluator observability payloads",
                "`tower_sim/loaders/wiki/cache_audit.py`: wiki cache audit",
            ],
            tests=[
                "`tests/test_repo_audit.py`",
                "`tests/test_stat_source_coverage.py`",
                "`tests/test_cache_audit.py`",
                "`tests/test_reference_completeness.py`",
            ],
            known_gaps=[
                "Reference-sheet parity pass/fail thresholds need a single release-gate policy.",
            ],
        ),
    ]


def _critical_path() -> list[str]:
    return [
        "Reconcile `IMPLEMENTATION_STATUS.md`, architecture checklist state, and this generated report each release cycle.",
        "Define v1 release-gate parity thresholds against Harry reference sheets (fixtures + tolerances).",
        "Tune assumptions-manifest parity tolerances over time using reference-sheet drift data.",
        "Harden tournament scenario coverage with explicit BC/heat fixtures and fail-closed checks.",
        "Keep economy and optional table expansions (`vault_stats_v1.csv`, `wse_presets_v1.csv`) scoped to v2 unless promoted by source data.",
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
