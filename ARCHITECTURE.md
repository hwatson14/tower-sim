# TowerSim Architecture (Codex Contract)

**Goal:** Deterministically evaluate run objectives (v1 focuses on boss-only Wmax) across farming/tournament/milestone contexts, and support optimisation (loadouts, perk policy, future spending, and respec mode).

**Authority override:** In case of conflict, `PROJECT_INTENT.md` overrides all documents.

## Core Principles
- **Library-driven:** mechanics and enemy tables live in libraries (CSV-backed or code tables with provenance), not embedded in calculators.
- **Deterministic only:** no hidden randomness. Deterministic envelope evaluation (explicit best/worst/nominal cases) is allowed.
- **Traceable composition:** every final stat is a composition of named sources in a fixed order.
- **Separation of concerns:** data loading, parsing, stat derivation, wave mapping, uptime, combat models, and optimisers are separate engines.
- **Fail-closed on missing inputs:** unknown mechanics or missing tables must raise explicit errors.

## System Pipeline (High Level)
Data sources → Parse → Build baseline account state → Apply run loadout → Apply tier rules → Wave progression engines → Combat model (boss) → Evaluators (objectives) → Outputs (metrics, margins) → Optimisers (later)

## v2 Additions: Architecture Planes (Preserve Existing Pipeline)
These planes describe where responsibilities live without changing the frozen stat pipeline.

1) **Reference (immutable)**
   - Authoritative libraries, tables, and canonical IDs.
   - Sources are the repo tables under `tables/` and the cached wiki tables under `tables/wiki_cache/`.
   - If a required table is missing or ambiguous, fail closed (see “Stop the Line”).

2) **Derivation (pure, side-effect-free)**
   - Inputs: `_IDS.csv` + run context (scenario definition) + loadout + account baseline.
   - Output: deterministic stat snapshots produced via the frozen composition order.

3) **Models / Simulation (mechanics)**
   - Mechanics-only engines (e.g., wave mapping, combat models) that evaluate outcomes for a fully specified scenario.
   - May use internal wave search, but external API must accept scenario parameters, not explicit wave queries.
   - CellModel is a first-class mechanics engine when authoritative tables exist; it must consume
     survivability outputs, wave time, elite presence, and kill rate rather than relying on a static lookup.
   - Uptime/overlap modeling must be steady-state (no timeline from wave 1) using explicit deterministic
     cases (e.g., no overlap / partial overlap / full overlap) derived from inputs or tables.
     If authoritative overlap rules are missing, mark the model incomplete rather than assuming probabilities.

4) **Evaluation (objectives)**
   - Converts model outputs into objective-aligned metrics (e.g., max wave).
   - Outputs are deterministic and may return explicit envelope cases (best / worst / nominal) derived from
     enumerated inputs. Stochastic sampling and invented distributions are not allowed.

5) **Planning + Optimisation**
   - Translates user intents into optimisation problems.
   - Optimisation has two tiers: (1) loadout optimisation (frequent) and (2) workshop respec optimisation (reallocate levels only; high-friction due to gem cost and limited frequency; treated as a separate mode).
   - Optimisers consume evaluators only, not low-level engines directly.

### Run Types
- **Farming run:** perks enabled; normal tier battle conditions.
- **Tournament run:** tournament BC set; perks disabled.
- **Milestone run:** perks enabled; uses tier rules; output includes milestone targets.

### Perk Handling (Deterministic Envelope)
Perk auto-pick priority order is a deterministic input. Evaluators must compute explicit,
enumerated perk-outcome cases consistent with that policy (best / worst / nominal), without sampling.
Perk envelopes may only use authoritative constraints present in the repo (perk pool, gating, max picks, etc.); if those are insufficient to define feasible envelopes, fail closed rather than invent an offer model.
If authoritative perk-offer rules are missing, the perk engine must be marked incomplete or fail closed.

## Data Sources (Authoritative)
Primary external input is `_IDS.csv` (player inventory + levels + equipped preset).
All other tables are shipped with the repo under `tables/` or `tables/wiki_cache/`,
and are treated as authoritative library data (with provenance).

### Snapshot Priority Order
1. **Local cache < 24 hours old**
2. **Git (tower-sim-data main)**
3. **Older cached snapshot(s)**

### IDS Path Resolution
Default `_IDS.csv` resolution order:
1. `tests/fixtures/tower-sim-data/_IDS.csv`
2. `tests/fixtures/_IDS.csv`
3. `reference/tower-sim-data/_IDS.csv`

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

## Intent → ProblemSpec (Deterministic Compilation)
User intent (e.g., farming tier, tournament league, milestone push) must be compiled into a deterministic `ProblemSpec` that includes:
- Resolved scenario (tier/league/mode + BC/heat/wave rules sources)
- Objective (which evaluator to run and what metrics to return)
- Decision space (what can be changed: loadout, perk policy, future spend)
- Constraints (inventory, budget)
This compiled spec must be logged/printed before optimisation runs. Any missing or ambiguous inputs must fail closed.

Resolved tournament scenarios must include the explicit tournament BC set as input;
do not infer tournament BCs per league unless a table is provided in the reference libraries.

## Determinism and Unknown Variability
Randomness is not permitted in this architecture. Determinism means identical declared inputs produce
identical outputs, including explicit envelope cases. Stochastic sampling and invented probability
distributions are not allowed. If a requested feature depends on stochastic mechanics without an
authoritative deterministic model, the sim must fail closed.

## Evaluator Contracts (Deterministic v1)
Evaluators are first-class and must remain deterministic under current rules. Any distribution/quantile
outputs require authoritative deterministic models and must be documented as missing until provided.

Canonical evaluators (contract definitions; implementations may be pending):
- **MaxWaveEvaluator**: returns max wave and diagnostics for a resolved scenario, plus any explicit
  envelope cases derived from deterministic inputs.
- **FarmRateEvaluator**: returns deterministic farm metrics and diagnostics *once* authoritative
  economy tables/models are present in the reference libraries, and may include explicit envelope cases.

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
- Computes deterministic uptime fractions and overlap fractions (explicit cases) consumed by economy and survivability models;
  no continuous timeline simulation.

### 8) Boss Combat Model (v1)
- Boss-only survivability.
- Inputs: wave_damage(tier, W_attack), stats at wave, tier BCs.
- Outputs: alive/dead margin, TTK, W_max (last survivable wave) + diagnostics.
- Contracts: use `failure_wave`/`w_fail` and `estimate_failure_wave()` or `find_w_max()` for wave naming.
- Search semantics: predicate `can_survive(w)`; return max `w` where `can_survive(w) == true`.
- Diagnostics/JSON output example:
  ```json
  {
    "w_max": 4478,
    "failure_wave": 4479,
    "limiting_factor": "boss_dps > regen",
    "notes": "Death Wave (UW) not involved"
  }
  ```

### 9) Validation Harness
- Compares outputs vs Harry’s reference sheets (authoritative).
- Wiki used secondarily with citations.

## Glossary (Concise)
- **Scenario:** A fully specified run context (tier/league/mode, battle conditions, heat rules, and wave damage sources).
- **Stat Snapshot:** A deterministic stat state at a specific phase (start-of-run, end-of-run, or at-wave W).
- **Run State:** The combination of baseline account state, loadout, in-run growth, and scenario.
- **Evaluator:** An objective-aligned function that turns model outputs into metrics for optimisation.
- **Optimiser:** A planner that searches a decision space using evaluators, not engine internals.
- **Perk Policy:** A deterministic rule for selecting perks when applicable (no RNG).

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
  - `reference/step1_dump_docs/part2_data/tier_battle_conditions.csv`
    (partial Tier 14–21 farming BC magnitudes; tiers 1–13 have none).

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
- [x] Add minimal eHP stat evaluator (mechanics YAML + IDS) for tower/wall HP slice.
- [x] Add helper to assemble split FULLREPO archive.
- [x] Add run context with tournament perk gating.
- [x] Thread RunContext through battle condition filtering and perk-gated stat composition.
- [x] Implement perk engine (perk bonus application with gating).
- [x] Implement tier battle condition loader (Tier BCs applied in frozen order).
- [x] Resolve `statbook_builder.py` API mismatch in StatBook pipeline.
- [x] Apply BC/heat in frozen stat order for at-wave snapshots consumed by combat.
- [x] Load tier/tournament wave damage tables from Step1 data dumps (strict lookup).
- [x] Add survivability pipeline entrypoint (StatEngine snapshots + verdict JSON).
- [ ] Define evaluator objective contracts and economy model inputs with authoritative provenance.
- [ ] Wire per-wave stat composition (progression + skip mapping → stat snapshots).
- [x] Wire skip mapping into StatEngine for at-wave stat snapshots.
- [x] Add data-driven combat engine scaffold (parameterized DR/thorns/PC).
- [x] Implement boss combat mechanics (PC/thorns/regen/DR) in boss_engine (v1 minimal).
- [ ] Implement boss combat model (boss-only survivability + W_max/failure_wave).
- [x] Implement boss combat model (boss-only survivability + W_max/failure_wave).
- [x] Implement boss survivability model (TTK/TTD resolution + BC loader + schema).
- [x] Wire wall thorns + plasma cannon card fractions into survivability pipeline + mechanics registry (wiki excerpt in prompt).
- [x] Add validation harness against Harry’s reference sheets.
- [x] Document missing mechanics cross-referenced to Step1 `/reference` parts 1–4.
- [x] Ingest Effective Paths reference sheets into an audit report.
- [x] Add Effective Paths formula token inventory and mechanics comparison report.
- [x] Add Effective Paths mechanics consolidation action list.
- [x] Add Effective Paths formula registry pack loader and tests.
- [x] Extract bot upgrade tables (DVT_Bot) into CSV + loader + tests.
- [x] Extract guardian upgrade tables (DVT_Guardians) into CSV + loader + tests.
- [x] Add perk effect and pool-weight tables from wiki excerpt (perks_v1.csv, perk_pool_weights_v1.csv).
- [x] Add assist stone efficiency table from wiki excerpt (assist_stone_levels_v1.csv).
- [x] Add recovery package module substat caps table from wiki excerpt (module_substats_v1.csv).
- [x] Add module main-effect base/step tables from Module Base Stat sheet (module_main_effect_bases_v1.csv, module_main_effect_bands_v1.csv).
- [x] Implement module main-effect multiplier formula (MODSTAT_*).
- [x] Add boss hit-interval table for survivability (boss_hit_interval_v1.csv).
- [x] Document run API task routing for agent usage.
- [ ] Populate vault stats table entries for eHP/vault multipliers (vault_stats_v1.csv).
- [ ] Populate WSE preset mapping table entries for eHP stats (wse_presets_v1.csv).
- [x] Add runtime evaluator for EP formula registry LAMBDAs (EPH_* execution wiring).
- [x] Wire Effective Paths eDamage LAMBDAs into derived stat pipeline (tower DPS/crit/ASPD).
- [x] Add token source mapping audit (token map, report, and validation script).
- [x] Add implementation status report generator (`python -m tower_sim.audit.status`).
- [x] Add IDS diagnostics dump script (schema-versioned JSON, missing-sections reporting, include-raw flag).
- [x] Add IDS dump GitHub Action (workflow dispatch + IDS change trigger).
- [x] Add IDS raw ingest + account snapshot compiler with preset-aware loadout resolution.
- [x] Switch survivability/max-wave report entrypoints to AccountSnapshot inputs.
- [x] Update run API inventory/loadout outputs to use AccountSnapshot snapshots.
- [x] Add spec loader + run API front door for deterministic W_max evaluation.
- [x] Add max-wave observability scaffolding (tier-1 result + tier-2 report).
- [x] Add deterministic MaxWaveEvaluator runner + fail-closed W_max search guardrails.
- [x] Add ignored `out/` directory and route runner outputs into it by default.
- [x] Add reference completeness report and runtime table guardrail test.
- [x] Promote Step1 part2 runtime tables (BC magnitudes, wave damage, tournament boss freq, DAG) with loaders/tests.
- [x] Add tournament heat BC magnitudes from Player & Stuff Battle Conditions sheet (user-provided table).
- [x] Document tiers 1–13 as having no battle conditions (user-provided clarification).
- [x] Consolidate audit report outputs under repo-root `audit/` (remove `tower_sim/audit` artifacts).
- [x] Add repo governance enforcement (REPO_MAP.yaml + validation script + tests).
- [x] Allow root .gitmodules in REPO_MAP allowed files.
- [x] Allow root GAME_OVERVIEW.md and PROJECT_INTENT.md in REPO_MAP allowed files.
- [x] Consolidate tier battle condition loaders onto step1 table parser + shim legacy loader.
- [x] Add identifier resolver with fail-closed eHP ledger closure guard.
- [x] Add card mastery table + loader with tests for sim access.
- [x] Sync Effective Paths eDamage mechanics to canonical extract (crit/ASPD/multishot/range/rapid fire/super tower).
- [x] Implement Effective Paths econ_current formulas + tests (Harry reference sheet).
- [x] Add allowlisted run task dispatcher (BASE_STATS/INVENTORY/LOADOUT/EHP_SLICE/MAX_WAVE).
- [x] Define task schemas + fail-closed validation for run dispatcher inputs.
- [x] Add unit tests covering run task dispatcher + core tasks.
- [x] Document agent-friendly IDS diagnostics usage for base stats, inventory, and loadout.
- [x] Confirm IDS dump artifacts are written under `audit/` after running the diagnostics helper.
