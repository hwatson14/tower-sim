# TowerSim Architecture (Codex Contract)

**Goal:** Deterministically compute the maximum reachable wave (boss-only survivability in v1) under different run contexts (farming, tournament, milestone), and later support optimisation (loadouts and future spending).

## Core Principles
- **Library-driven:** mechanics and enemy tables live in libraries (CSV-backed or code tables with provenance), not embedded in calculators.
- **Deterministic by default:** expected-value simulation only; no randomness.
- **Traceable composition:** every final stat is a composition of named sources in a fixed order.
- **Separation of concerns:** data loading, parsing, stat derivation, wave mapping, uptime, combat models, and optimisers are separate engines.
- **Fail-closed on missing inputs:** unknown mechanics or missing tables must raise explicit errors.

## System Pipeline (High Level)
Data sources → Parse → Build baseline account state → Apply run loadout → Apply tier rules → Wave progression engines → Combat model (boss) → Outputs (max wave, margins) → Optimisers (later)

### Run Types
- **Farming run:** perks enabled, normal tier battle conditions.
- **Tournament run:** tournament BC set; perks disabled unless explicitly enabled.
- **Milestone run:** uses tier rules; output includes milestone targets.

## Data Sources (Authoritative)
Primary external input is `_IDS.csv` (player inventory + levels + equipped preset).
All other tables are shipped with the repo under `tower_sim/tables` or `tower_sim/wiki/cache`,
and are treated as authoritative library data (with provenance).

### Snapshot Priority Order
1. **Local cache < 24 hours old**
2. **Git (tower-sim-data main)**
3. **Older cached snapshot(s)**

### IDS Path Resolution
Default `_IDS.csv` resolution order:
1. `tests/fixtures/tower-sim-data/_IDS.csv`
2. `tests/fixtures/_IDS.csv`
3. `data/tower-sim-data/_IDS.csv`

## State Model
### A) Account Baseline (unchanged during a run)
- Labs
- Workshop (base levels; start-of-run uses ¢ levels; end-of-run uses $ levels)
- Ultimate Weapons (unlocks + 3 track levels; UW+ placeholder)
- Relics
- Themes/songs
- Vault

### B) Run Loadout (selected for the run)
- Modules (primary + assist; substats)
- Cards (equipped preset)
- Bots
- Guardians

### C) In-run Growth (must be modelled deterministically)
- Free upgrades → workshop level progression over waves
- Wave skips (EALS/EHLS mapping W_actual → W_attack/W_health)
- Any explicitly modelled ramps (e.g. DW health ramp later)

## Stat Composition Order (Frozen)
All stat values must be composed in this exact order:

1. **Base sources** (workshop + labs + relics + account bonuses)
2. **Loadout sources** (modules + cards + bots + guardians + passive UW effects)
3. **Enhancements** (multiplicative on the final combined stat)
4. **Tier rules** (battle conditions, tournament perk-disable, tier adjustments)
5. **Derived** (convert % to absolute, compute caps, convenience derived stats)

## StatBook (First-Class Artifact)
TowerSim must produce a StatBook that is both:
- machine-consumable by the sim, and
- human-readable for inspection.

### Stat Registry (Canonical IDs + Units)
Stat identities, units, and allowed phases are centrally defined in the StatRegistry.
All StatBook rows must reference a registry stat_id; unknown IDs fail closed.
The registry is also exported alongside StatBook rows for inspection.

**StatBook rows** should include:
- `stat_id`
- `phase` (start-of-run, end-of-run, at-wave W)
- `base_value`
- `loadout_delta`
- `enhancement_multiplier`
- `tier_rule_delta_or_multiplier`
- `final_value`
- `provenance` (sheet cell/table or wiki citation)

Export formats:
- `statbook.csv`
- optional: `statbook.xlsx`

## Engines
### 1) DataLoader
- Resolves snapshot folder using priority order.
- Returns a DatasetBundle: file paths + timestamps + hashes.
- Repository tables are treated as local libraries (no snapshot dependency).

### 2) IDS Parser
- Parses `_IDS.csv` into a typed `IdsState` (raw values only, no mechanics).

### 3) Mechanics Libraries
- Workshop value lookup tables
- Labs library (formula-first with table fallback)
- Cards library
- Modules library (primary + assist + substats)
- Perks library
- Enemy wave damage library (strict lookup)

### 4) Stat Engine
- Produces `RunStats` snapshots and StatBook rows from `IdsState` + run loadout + tier.

### 5) Workshop Progression Engine
- Deterministic expected-value free upgrades.
- Produces workshop level curves over waves.

### 6) Skip Mapping Engine
- Uses EALS/EHLS as a function of wave.
- Outputs mapping from W_actual to W_attack and W_health (expected floor mapping).

### 7) Uptime Engine (later for v1.5)
- Uses wave time model and package chance.
- Outputs average uptime multipliers that combat model consumes.

### 8) Boss Combat Model (v1)
- Boss-only survivability.
- Inputs: wave_damage(tier, W_attack), stats at wave, tier BCs.
- Outputs: alive/dead margin, TTK, death wave estimate.

### 9) Validation Harness
- Compares outputs vs Harry’s reference sheets (authoritative).
- Wiki used secondarily with citations.

## Missing Mechanics Cross-Check (Step1 Parts 1–4)
The current sim is still missing these mechanics. The Step1 `/reference` bundle
contains the authoritative recovery details; each item below lists where the
mechanic details live in parts 1–4:

### Combat Engines (boss + nonboss)
- **Missing mechanic:** combat resolution engines (boss survivability + nonboss
  combat loop).
- **Reference location:** `reference/step1_dump_docs/part3_refs_tests_docs/docs/RECOVERY_GAPS.md`
  (explicitly notes `sim/engines/combat_engine.py` and
  `sim/engines/nonboss_combat_engine.py` are missing).

### Tier Battle Conditions + Heat
- **Missing mechanic:** tier BC application in frozen order + heat scaling.
- **Reference locations:**
  - `reference/step1_dump_docs/part1_core/DATA_BINDING.md` (expects
    `battle_conditions.csv` + `heat.csv` runtime inputs).
  - `reference/step1_dump_docs/part3_refs_tests_docs/docs/BC_HEAT_SOURCE.md`
    and `BC_HEAT_PROVENANCE.md` (source + gaps).
  - `reference/step1_dump_docs/part2_data/battle_condition_magnitudes.csv`
    (BC base magnitude table).
  - `reference/step1_dump_docs/part2_data/heat_wave_scalar.csv` (league,wave heat).
  - `reference/step1_dump_docs/part2_data/tier14_21_battle_conditions.csv`
    (partial Tier 14–21 farming BC magnitudes).

### Tournament Battle Conditions
- **Missing mechanic:** tournament BC magnitudes (per-wave) and league-specific
  boss frequency.
- **Reference locations:**
  - `reference/step1_dump_docs/part2_data/tournament_bc_magnitudes_from_player_and_stuff.csv`
    (per-wave BC magnitudes).
  - `reference/step1_dump_docs/part2_data/tournament_more_bosses_static.csv`
    (boss frequency by league).

### Wave Damage Curves
- **Missing mechanic:** authoritative wave damage curves for tier + tournament.
- **Reference locations:**
  - `reference/step1_dump_docs/part2_data/tier_wave_damage.csv`
  - `reference/step1_dump_docs/part2_data/tournament_wave_damage.csv`

### Runtime DAG / Derived Pipeline Inputs
- **Missing mechanic:** DAG-defined derived stat pipeline (tiers.csv + dag.json
  binding).
- **Reference locations:**
  - `reference/step1_dump_docs/part1_core/DATA_BINDING.md` (expects `tiers.csv`
    + `dag.json` at runtime).
  - `reference/step1_dump_docs/part2_data/dag.json` (DAG snapshot).

## “Stop the Line” Conditions
Any of the following must stop work and ask for clarification:
- A mechanic is required but not specified by sheet/wiki.
- A table/constant is missing.
- Two sources conflict (sheet vs wiki).
- A unit test cannot be written because input format is unknown.

## Near-Term Implementation Plan (Codex)
1. Implement typed `_IDS` → `IdsState` + tests.
2. Implement DataLoader integration with `tower-sim-data` snapshots + tests.
3. Implement Stat Engine skeleton + StatBook export.
4. Wire workshop progression + skip mapping into per-wave stat snapshots.
5. Implement boss-only combat model + validate vs sheets.

## Checklist
- [x] Implement typed `_IDS.csv` parsing to `IdsState` (raw values only) + tests.
- [x] Restrict external inputs to `_IDS.csv` (repo tables serve as libraries).
- [x] Add StatBook skeleton/export and reference structure validation harness.
- [x] Add wiki cache audit harness and reports for promotable lab tables.
- [x] Add canonical StatBook export schema with loadout delta breakdown scaffolding.
- [x] Promote labs values v1 table from audited cache tables.
- [x] Add stat source coverage audit for labs and workshop tables.
- [x] Implement stat engine base composition (workshop + labs + EALS/EHLS + canonical StatBook rows).
- [x] Implement Stat Engine skeleton + StatBook export.
- [x] Add helper to assemble split FULLREPO archive.
- [x] Add run context with tournament perk gating.
- [x] Thread RunContext through battle condition filtering and perk-gated stat composition.
- [x] Implement perk engine (perk bonus application with gating).
- [x] Implement tier battle condition loader (Tier BCs applied in frozen order).
- [x] Resolve `statbook_builder.py` API mismatch in StatBook pipeline.
- [ ] Wire per-wave stat composition (progression + skip mapping → stat snapshots).
- [x] Add data-driven combat engine scaffold (parameterized DR/thorns/PC).
- [ ] Implement boss combat model (boss-only survivability + death wave).
- [x] Implement boss survivability model (TTK/TTD resolution + BC loader + schema).
- [ ] Add validation harness against Harry’s reference sheets.
- [x] Document missing mechanics cross-referenced to Step1 `/reference` parts 1–4.
- [x] Ingest Effective Paths reference sheets into an audit report.
- [x] Add Effective Paths formula token inventory and mechanics comparison report.
