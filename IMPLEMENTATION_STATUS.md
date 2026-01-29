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
- `tower_sim/sources.py` provides an IDS-only resolver (`load_ids_only_bundle`) for `_IDS.csv`.
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
- `tower_sim/libs/wave_damage_strict.py` provides strict lookup tables for selected tiers/modes.

### Modules
- `tower_sim/libs/modules_library.py`, `tower_sim/engines/modules.py`, `tower_sim/libs/assist_efficiency.py` implement module unique effects, substats, and assist efficiency logic.

### Tier Battle Conditions
- `tower_sim/loaders/tier_bc_loader.py` loads tier 14–21 farming BC magnitudes from `tables/tier14_21_battle_conditions.csv`.

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

### Stat Engine + StatBook
- Stat engine scaffolding and StatBook export exist, but composition is incomplete.

### Tier Rules / Battle Conditions
- `tower_sim/engines/battle_conditions.py` exists, but the Tier BC loader is not yet wired into per-wave stat composition or applied in frozen order.
- Tournament run rules (perks disabled, permanent BCs) not fully wired; perks gate helper exists in `tower_sim/perks_gate.py`.
### Missing (Explicit)
- Tier BC application in per-wave stat composition (loader exists but is not yet integrated).
- Per-wave stat composition (progression + skip mapping not yet feeding stat snapshots).
- Boss combat model (boss-only survivability and death wave estimation).
- Validation harness against Harry’s reference sheets.
- Deterministic intent compiler (user intent → ProblemSpec) and evaluator layer (objective metrics).
- Optimisers that consume evaluators only (loadout, perk policy, stone spend).
- Deterministic perk-offer model (explicit envelope cases driven by policy; no sampling).
- Economy model tables for deterministic farming metrics (coins/hr, cells/hr).

### Missing Mechanics Cross-Check (Step1 Parts 1–4)
The Step1 `/reference` bundle contains the missing mechanics and their data
sources. This list maps each missing mechanic in the current sim to the
corresponding Step1 part file(s):

#### Combat Engines (boss + nonboss)
- **Missing mechanic:** combat resolution engines (boss survivability + nonboss
  combat loop).
- **Reference location:** `reference/step1_dump_docs/part3_refs_tests_docs/docs/RECOVERY_GAPS.md`
  (explicit missing `sim/engines/combat_engine.py` and
  `sim/engines/nonboss_combat_engine.py`).

#### Tier Battle Conditions + Heat
- **Missing mechanic:** tier BC application in frozen order + heat scaling.
- **Reference locations:**
  - `reference/step1_dump_docs/part1_core/DATA_BINDING.md` (`battle_conditions.csv`,
    `heat.csv` runtime inputs).
  - `reference/step1_dump_docs/part3_refs_tests_docs/docs/BC_HEAT_SOURCE.md`
    and `BC_HEAT_PROVENANCE.md` (source + gaps).
  - `reference/step1_dump_docs/part2_data/battle_condition_magnitudes.csv`
    (BC base magnitude table).
  - `reference/step1_dump_docs/part2_data/heat_wave_scalar.csv`
    (league,wave heat).
  - `reference/step1_dump_docs/part2_data/tier14_21_battle_conditions.csv`
    (partial Tier 14–21 farming BC magnitudes).

#### Tournament Battle Conditions
- **Missing mechanic:** tournament BC magnitudes (per-wave) and league-specific
  boss frequency.
- **Reference locations:**
  - `reference/step1_dump_docs/part2_data/tournament_bc_magnitudes_from_player_and_stuff.csv`
  - `reference/step1_dump_docs/part2_data/tournament_more_bosses_static.csv`

#### Wave Damage Curves
- **Missing mechanic:** authoritative wave damage curves for tier + tournament.
- **Reference locations:**
  - `reference/step1_dump_docs/part2_data/tier_wave_damage.csv`
  - `reference/step1_dump_docs/part2_data/tournament_wave_damage.csv`

#### Runtime DAG / Derived Pipeline Inputs
- **Missing mechanic:** DAG-defined derived stat pipeline (tiers.csv + dag.json
  binding).
- **Reference locations:**
  - `reference/step1_dump_docs/part1_core/DATA_BINDING.md` (`tiers.csv` + `dag.json`).
  - `reference/step1_dump_docs/part2_data/dag.json`.

### Boss Survivability Model (v1 objective)
- Boss-only combat model (PC + thorns + regen + DR) implemented in
  `tower_sim/combat/boss_engine.py` with v1 minimal mechanics (percent-current
  PC + thorns, defense/DR mitigation, regen + package heal expectation).
- Fail-closed boss combat engine scaffold exists in `tower_sim/combat/boss_engine.py`.
- No root-find / binary search to find death wave.

### Validation Harness
- No harness comparing outputs to Harry’s reference sheets.

### Optimisers (Later)
- Loadout optimiser and stone spending optimiser not implemented.

## Immediate Next Steps (Codex PR sequence)
1. Resolve `statbook_builder.py` API mismatch + tests.
2. Wire progression + skip mapping to produce per-wave stats.
3. Implement boss-only combat model and validate against reference sheets.
4. Add validation harness against Harry’s reference sheets.
