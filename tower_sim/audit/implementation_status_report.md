# Implementation Status Report

Regenerate with:

```bash
python -m tower_sim.audit.status
```

## Component status table

| Component | Status | Evidence | Tests | Known gaps |
| --- | --- | --- | --- | --- |
| Ids parsing | implemented | `tower_sim/ids_parser.py`: `parse_ids`, section parsing<br>`tower_sim/ids_state.py`: typed `IdsState` | `tests/test_ids_parser.py` | — |
| DataLoader | partial | `tower_sim/sources.py`: `load_snapshot_bundle`, `load_ids_only_bundle` | `tests/test_sources.py` | No spec-driven loader or snapshot selection wired into a run entrypoint. |
| Stat engine | partial | `tower_sim/stat_engine.py`: `StatEngine`, `StatInput`<br>`tower_sim/stat_registry.py`: `default_registry` | `tests/test_stat_engine.py`<br>`tests/test_stat_engine_tier_rules.py` | Derived stat composition/DPS formulas are incomplete; see [Effective Paths mechanics comparison](tower_sim/audit/effective_paths_mechanics_comparison.md#effective-paths-v50001-master-workbook). |
| Statbook builder | implemented | `tower_sim/statbook.py`: StatBook schema<br>`tower_sim/statbook_builder.py`: `build_statbook`, `build_canonical_statbook` | `tests/test_statbook_builder.py`<br>`tests/test_statbook_reference_structure.py` | — |
| Workshop progression | partial | `tower_sim/workshop_progression.py`: `simulate_workshop_progression` | `tests/test_workshop_progression.py` | Free Upgrade allocation policy is fail-closed; see [Workshop / WS+ / Free upgrades](tower_sim/audit/effective_paths_mechanics_comparison.md#workshop--ws---free-upgrades). |
| Skip mapping | implemented | `tower_sim/wave_engine.py`: `SkipRamp`, `expected_skipped_waves`, `make_wave_state` | `tests/test_wave_engine.py` | — |
| BC/heat | partial | `tower_sim/battle_conditions.py`: `BattleConditions`<br>`tower_sim/tier_bc_loader.py`: `load_tier_battle_conditions`<br>`tower_sim/tournament_bc_selection.py`: league BC enumeration | `tests/test_battle_conditions_context.py`<br>`tests/test_tier_battle_conditions.py`<br>`tests/test_tier_bc_loader.py`<br>`tests/test_tournament_bc_selection.py` | Heat curves are loaded from tables, but no end-to-end run integration. |
| Wave damage | partial | `tower_sim/enemies/wave_damage_strict.py`: strict wave damage library | `tests/test_imports.py` | Only sparse anchor tables; full per-wave tables are not loaded. |
| Boss combat | stub | `tower_sim/combat/boss_engine.py`: fail-closed placeholder<br>`tower_sim/combat/boss_survivability.py`: TTK/TTD resolution | `tests/test_boss_engine.py`<br>`tests/test_boss_survivability.py` | Boss combat mechanics (PC, thorns, regen, DR) are not implemented. |
| Evaluator | missing | No `MaxWaveEvaluator` implementation in `tower_sim/`. | — | No deterministic Wmax evaluation pipeline exists. |
| CLI | missing | No `python -m tower_sim.run` entrypoint exists. | — | Spec parsing/dispatch not implemented. |
| Validation harness | partial | `tower_sim/audit/repo_audit.py`: repo audit CLI<br>`tower_sim/audit/stat_source_coverage.py`: stat source coverage<br>`tower_sim/wiki/cache_audit.py`: wiki cache audit | `tests/test_repo_audit.py`<br>`tests/test_stat_source_coverage.py`<br>`tests/test_cache_audit.py` | No validation harness against Harry’s reference sheets. |

## Critical path to a runnable MaxWaveEvaluator (deterministic Wmax JSON)

- Define a run spec schema + parser for `python -m tower_sim.run --spec <fixture>`.
- Implement a deterministic `MaxWaveEvaluator` that wires IDS + snapshot inputs.
- Integrate per-wave stat composition (workshop progression + skip mapping).
- Wire battle conditions and heat selections into per-wave stats.
- Load authoritative per-wave enemy damage tables (replace strict anchors).
- Implement boss combat mechanics with authoritative formulas (PC/thorns/regen/DR).
- Compute wave outcomes deterministically and emit Wmax JSON.
- Add end-to-end validation harness vs reference sheets once available.
