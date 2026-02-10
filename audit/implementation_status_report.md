# Implementation Status Report

Regenerate with:

```bash
python -m tower_sim.audit.status
```

## Component status table

| Component | Status | Evidence | Tests | Known gaps |
| --- | --- | --- | --- | --- |
| Ids parsing | implemented | `tower_sim/loaders/ids_parser.py`: `parse_ids`, section parsing<br>`tower_sim/util/ids_raw.py`: raw `_IDS.csv` ingest | `tests/test_ids_parser.py` | — |
| DataLoader | implemented | `tower_sim/loaders/sources.py`: `load_snapshot_bundle`, `load_ids_only_bundle`<br>`tower_sim/loaders/account_snapshot_loader.py`: snapshot JSON ingest<br>`tower_sim/loaders/account_snapshot_compiler.py`: preset-aware account snapshot compilation | `tests/test_sources.py`<br>`tests/test_account_snapshot_compiler.py` | Remote snapshot fetch/pull is not implemented; loader is local-file based. |
| Stat engine | partial | `tower_sim/engines/stat_engine.py`: `StatEngine`, `StatInput`<br>`tower_sim/registry/stat_registry.py`: `default_registry`<br>`tower_sim/engines/stat_snapshots.py`: at-wave snapshot composition | `tests/test_stat_engine.py`<br>`tests/test_stat_engine_tier_rules.py`<br>`tests/test_stat_snapshots.py` | Derived stat composition/DPS formulas are incomplete; see [Effective Paths mechanics comparison](audit/effective_paths_mechanics_comparison.md#effective-paths-v50001-master-workbook). |
| Statbook builder | implemented | `tower_sim/util/statbook.py`: StatBook schema<br>`tower_sim/engines/statbook_builder.py`: `build_statbook`, `build_canonical_statbook` | `tests/test_statbook_builder.py`<br>`tests/test_statbook_reference_structure.py` | — |
| Workshop progression | partial | `tower_sim/engines/workshop_progression.py`: `simulate_workshop_progression`<br>`tower_sim/engines/free_upgrades.py`: deterministic expected free-upgrade model | `tests/test_workshop_progression.py` | Free Upgrade allocation policy is fail-closed; see [Workshop / WS+ / Free upgrades](audit/effective_paths_mechanics_comparison.md#workshop--ws---free-upgrades). |
| Skip mapping | implemented | `tower_sim/engines/wave_engine.py`: `SkipRamp`, `expected_skipped_waves`, `make_wave_state` | `tests/test_wave_engine.py` | — |
| BC/heat | partial | `tower_sim/engines/battle_conditions.py`: `BattleConditions`<br>`tower_sim/loaders/tier_bc_loader.py`: tier BC table loading<br>`tower_sim/loaders/bc_heat_loader.py`: tournament heat lookup<br>`tower_sim/loaders/tournament_bc_selection.py`: league BC enumeration | `tests/test_battle_conditions_context.py`<br>`tests/test_tier_bc_loader.py`<br>`tests/test_bc_heat_loader.py`<br>`tests/test_tournament_bc_selection.py` | Unsupported BC families intentionally fail closed (`SUPPORTED_BC` allowlist). |
| Wave damage | implemented | `tower_sim/libs/wave_damage_strict.py`: strict enemy HP/damage tables with log-linear interpolation | `tests/test_wave_damage_strict.py` | Only canonical HP/damage are represented; non-boss combat mechanics remain separate work. |
| Boss combat | implemented | `tower_sim/engines/combat/boss_engine.py`: deterministic PC/thorns/regen/DR core<br>`tower_sim/engines/combat/boss_survivability.py`: TTK/TTD resolution<br>`tower_sim/engines/combat/combat_engine.py`: survivability integration | `tests/test_boss_engine.py`<br>`tests/test_boss_survivability.py`<br>`tests/test_combat_engine.py` | Model scope is boss survivability for v1; nonboss combat loop remains out of scope. |
| Evaluator | implemented | `tower_sim/evaluators/max_wave.py`: deterministic `MaxWaveEvaluator`<br>`tower_sim/evaluators/max_wave_report.py`: report-friendly output adapters | `tests/test_max_wave_v1_contract.py`<br>`tests/test_max_wave_observability.py`<br>`tests/test_run_api.py` | Economy objectives are deferred; v1 focuses on deterministic `MAX_WAVE`. |
| CLI | partial | `tower_sim/run/runner.py`: fixture runner CLI entrypoint<br>`tower_sim/run/api.py`: allowlisted deterministic task dispatcher | `tests/test_run_runner.py`<br>`tests/test_run_api.py`<br>`tests/test_run_context.py` | Runner CLI currently targets repo fixture defaults; user-facing CLI ergonomics are limited. |
| Validation harness | partial | `tower_sim/audit/repo_audit.py`: repo audit CLI<br>`tower_sim/audit/stat_source_coverage.py`: stat source coverage<br>`tower_sim/evaluators/max_wave_report.py`: evaluator observability payloads<br>`tower_sim/loaders/wiki/cache_audit.py`: wiki cache audit | `tests/test_repo_audit.py`<br>`tests/test_stat_source_coverage.py`<br>`tests/test_cache_audit.py`<br>`tests/test_reference_completeness.py` | Reference-sheet parity pass/fail thresholds need a single release-gate policy. |

## Critical path to a runnable MaxWaveEvaluator (deterministic Wmax JSON)

- Reconcile `IMPLEMENTATION_STATUS.md`, architecture checklist state, and this generated report each release cycle.
- Define v1 release-gate parity thresholds against Harry reference sheets (fixtures + tolerances).
- Tune assumptions-manifest parity tolerances over time using reference-sheet drift data.
- Harden tournament scenario coverage with explicit BC/heat fixtures and fail-closed checks.
- Keep economy and optional table expansions (`vault_stats_v1.csv`, `wse_presets_v1.csv`) scoped to v2 unless promoted by source data.
