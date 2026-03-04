> **Role:** Status-only implementation audit.

# TowerSim Implementation Status (Truthful Audit)

This document describes what is implemented in the bundled code at the time of packaging, and what remains stubbed/missing. It is intended to prevent “README optimism”.

## Canonical Baseline Used
Base code assembled from:
- `towersim_wave_freeupgrades_patch_v2.zip` (primary baseline)
Merged additions:
- `towersim_wiki_ingest_v6.zip` (perks + EALS/EHLS lab tables)
- `towersim_enemy_wave_damage_lib.zip` (strict enemy wave damage library)

Explicitly NOT included:
- `towersim_modules_library_v2.zip` (inconsistent enum usage; treated as invalid)
- older `codebase_wip_v6/v7/v8` (superseded by the baseline)

## What is Implemented (High Confidence)
### Data + Input Loading
- `_IDS.csv` is the only external input; the rest of the tables ship with the repo.
- `tower_sim/loaders/sources.py` provides an IDS-only resolver (`load_ids_only_bundle`) for `_IDS.csv`.
- Snapshot helpers remain available for legacy workflows.

### IDS Parsing
- `tower_sim/loaders/ids.py` implements **section splitting** of `_IDS.csv` into named sections.
- Typed `IdsState` parsing exists for raw values.

### Workshop Progression (Deterministic)
- `tower_sim/engines/free_upgrades.py` implements deterministic expected free upgrades.
- `tower_sim/engines/workshop_progression.py` implements expected-value workshop progression over waves.

### Skip Mapping (Deterministic)
- `tower_sim/engines/wave_engine.py` implements EALS/EHLS ramp and expected mapping from `W_actual` → `W_attack` / `W_health`.

### Enemy Tables
- `tower_sim/libs/enemy_tables.py` provides wave damage CSV loader with compact-number parsing.
- `tower_sim/libs/wave_damage_strict.py` provides canonical enemy HP/Damage table loading from `tables/enemy_health_table.csv` and `tables/enemy_damage_table.csv`, with log-linear per-wave interpolation (linear in ln(value)).

### Modules
- `tower_sim/libs/modules_library.py`, `tower_sim/engines/modules.py`, `tower_sim/libs/assist_efficiency.py` implement module unique effects, substats, and assist efficiency logic.

### Tier Battle Conditions
- `tower_sim/loaders/tier_bc_loader.py` loads tier 14–21 farming BC magnitudes from `tables/tier_battle_conditions.csv`.
- Tiers 1–13 have no battle conditions (user-provided clarification).

### Wiki Caches + Ingest
- `tower_sim/loaders/wiki/cards.py` reads cached card tables.
- `tower_sim/loaders/wiki/labs.py` + `labs_ingest_all.py` + `labs_formula.py` implement lab value retrieval with formula-first and cache fallback.
- `tower_sim/loaders/wiki/perks.py` provides perk effectiveness helpers.
- `tower_sim/loaders/wiki/labs_eals_ehls.py` provides helpers for EALS/EHLS lab tables.

### Uptime / Wave Time (Partial)
- `tower_sim/engines/wave_time.py` and `tower_sim/engines/uptime.py` exist but are not yet validated against authoritative references.

## What is NOT Implemented (Known Gaps)
### Core Architecture Gaps
- Legacy snapshot loader does not fetch/pull remotes (local git dir only).

### Partially Implemented Areas (fail-closed where applicable)
- Stat engine scaffolding and StatBook export exist; canonical stat-input component composition is implemented (including AT_WAVE extraction), but broader derived DPS/stat-path coverage remains incomplete.
- Tier BC + heat application is wired into canonical at-wave stat composition for supported BC families.
- Unsupported BC families intentionally fail closed via `SUPPORTED_BC` allowlist until authoritative handling is added.
- Validation harness tooling exists, but parity threshold policy/tolerance calibration against Harry reference sheets remains in progress.

### Missing (Explicit)
- Non-boss combat loop remains out of scope for v1 MAX_WAVE and is not implemented.
- Optimisers that consume evaluators only (loadout, perk policy, stone spend).
- Deterministic perk-offer model (explicit envelope cases driven by policy; no sampling).
- Economy model tables for deterministic farming metrics (coins/hr, cells/hr).

### Missing Mechanics Cross-Check (Step1 Parts 1–4)
The Step1 `/reference` bundle contains the missing mechanics and their data
sources. This list maps each missing mechanic in the current sim to the
corresponding Step1 part file(s):

#### Combat Engines (boss + nonboss)
- **Current state:** boss survivability combat resolution is implemented for v1;
  nonboss combat loop remains missing.
- **Reference location:** `tables/step1_dump_docs/part3_refs_tests_docs/docs/RECOVERY_GAPS.md`
  (historical recovery inventory including nonboss loop gaps).

#### Tier Battle Conditions + Heat
- **Current state:** tier BC application + heat scaling are implemented for
  supported BC families in canonical at-wave pipeline; unresolved families fail
  closed.
- **Reference locations:**
  - `tables/step1_dump_docs/part1_core/DATA_BINDING.md` (`battle_conditions.csv`,
    `heat.csv` runtime inputs).
  - `tables/step1_dump_docs/part3_refs_tests_docs/docs/BC_HEAT_SOURCE.md`
    and `BC_HEAT_PROVENANCE.md` (source + gaps).
  - `tables/step1_dump_docs/part2_data/battle_condition_magnitudes.csv`
    (BC base magnitude table).
  - `tables/step1_dump_docs/part2_data/heat_wave_scalar.csv`
    (league,wave heat).
  - `tables/step1_dump_docs/part2_data/tier_battle_conditions.csv`
    (partial Tier 14–21 farming BC magnitudes; tiers 1–13 have none).

#### Tournament Battle Conditions
- **Current state:** tournament BC magnitudes are partially implemented with
  fail-closed behavior for unresolved families.
- **Reference locations:**
  - `tables/step1_dump_docs/part2_data/tournament_bc_magnitudes_from_player_and_stuff.csv`
  - `tables/step1_dump_docs/part2_data/tournament_more_bosses_static.csv`

#### Wave Damage / Health Curves
- **Implemented mechanic:** canonical enemy scaling sourced from:
  - `tables/enemy_damage_table.csv`
  - `tables/enemy_health_table.csv`
  with log-linear interpolation between anchor waves.

#### Runtime DAG / Derived Pipeline Inputs
- **Current state:** DAG table (`dag.json`) is validated and bound into canonical runtime stat pipeline diagnostics with fail-closed missing/invalid handling.
- **Reference locations:**
  - `tables/step1_dump_docs/part1_core/DATA_BINDING.md` (`tiers.csv` + `dag.json`).
  - `tables/step1_dump_docs/part2_data/dag.json`.

### Boss Survivability Model (v1 objective)
- Boss-only combat model (PC + thorns + regen + DR) implemented in
  `tower_sim/engines/combat/boss_engine.py` with v1 minimal mechanics (percent-current
  PC + thorns, defense/DR mitigation, regen + package heal expectation).
- Boss survivability integration is wired through evaluator search (`exponential_binary` and `grid_refine` strategies) in `tower_sim/evaluators/max_wave.py`.

## Immediate Next Steps (Codex PR sequence)
1. Reconcile this document with `audit/implementation_status_report.md` on every release cut.
2. Keep the v1 release-gate parity policy enforced and calibrated against Harry-sheet drift data each release.
3. Keep tournament scenario coverage explicit (Champion + Legend BC/heat fixtures) and fail closed on unresolved BC families.

## V1 Closeout Task Board

Source for current component state: `audit/implementation_status_report.md`.

- [x] Reconcile architecture checklist state with implemented evaluator contracts and boss combat status.
- [x] Convert immediate next steps into release-focused tasks instead of stale implementation milestones.
- [x] Lock and automate a single parity threshold policy for reference-sheet validation in release-gate tests (`tests/test_max_wave_v1_contract.py`, `tests/test_release_gate_tournament_fixtures.py`).
- [ ] Keep assumptions-manifest tolerances calibrated with reference-sheet drift data and document updates each release.

## Operational quick reference (status/ops, non-authority)
This section captures practical run/artifact details previously kept in README so operators and agents can execute and validate workflows without expanding the authoritative doc surface.

### Published/expected output artifacts
- `out/ids_dump_latest.json` (canonical IDS dump snapshot payload)
- `out/base_stats_latest.json`
- `out/inventory_latest.json`
- `out/loadout_latest.json`
- `out/base_stats_components_latest.json`
- `out/inventory_components_latest.json`
- `out/run_stats_latest.json`
- `out/max_wave_latest.json`
- `out/lineage_manifest_latest.json`
- `out/runner_output_latest.json` (CI-published runner payload when workflow emits it)

### Canonical local commands
Run deterministic MAX_WAVE spine:
```bash
python -m tower_sim.run --spec fixtures/specs/max_wave.yaml
```

Stat lineage burn-down report:
```bash
python -m tower_sim.audit.stat_lineage_report \
  --manifest out/stat_lineage_manifest_latest.json \
  --json-out out/stat_lineage_report_latest.json
```

Wiring health scorecard:
```bash
python -m tower_sim.audit.wiring_health_check \
  --ids tests/fixtures/tower-sim-data/_IDS.csv \
  --lineage-manifest out/stat_lineage_manifest_latest.json \
  --output out/wiring_health_check.json
```

### Agent routing hints (task-level)
- `BASE_STATS`: deterministic base statbook projection.
- `INVENTORY`: deterministic inventory snapshot output.
- `LOADOUT`: deterministic resolved loadout output.
- `MAX_WAVE`: deterministic max-wave objective evaluation.

If required IDS/spec inputs are missing, tasks should fail closed with explicit missing-input diagnostics.
