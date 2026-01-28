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
- `towersim/ids.py` implements **section splitting** of `_IDS.csv` into named sections.
- Typed `IdsState` parsing exists for raw values.

### Workshop Progression (Deterministic)
- `towersim/free_upgrades.py` implements deterministic expected free upgrades.
- `towersim/workshop_progression.py` implements expected-value workshop progression over waves.

### Skip Mapping (Deterministic)
- `towersim/wave_engine.py` implements EALS/EHLS ramp and expected mapping from `W_actual` → `W_attack` / `W_health`.

### Enemy Tables
- `towersim/enemy_tables.py` provides wave damage CSV loader with compact-number parsing.
- `towersim/enemies/wave_damage_strict.py` provides strict lookup tables for selected tiers/modes.

### Modules
- `towersim/modules_library.py`, `towersim/modules.py`, `towersim/assist_efficiency.py` implement module unique effects, substats, and assist efficiency logic.

### Tier Battle Conditions
- `tower_sim/tier_bc_loader.py` loads tier 14–21 farming BC magnitudes from `tower_sim/tables/tier14_21_battle_conditions.csv`.

### Wiki Caches + Ingest
- `towersim/wiki/cards.py` reads cached card tables.
- `towersim/wiki/labs.py` + `labs_ingest_all.py` + `labs_formula.py` implement lab value retrieval with formula-first and cache fallback.
- `towersim/wiki/perks.py` provides perk effectiveness helpers.
- `towersim/wiki/labs_eals_ehls.py` provides helpers for EALS/EHLS lab tables.

### Uptime / Wave Time (Partial)
- `towersim/wave_time.py` and `towersim/uptime.py` exist but are not yet validated against authoritative references.

## What is NOT Implemented (Known Gaps)
### Core Architecture Gaps
- Legacy snapshot loader does not fetch/pull remotes (local git dir only).

### Stat Engine + StatBook
- Stat engine scaffolding and StatBook export exist, but composition is incomplete.
- `statbook_builder.py` API mismatch remains a known gap.

### Tier Rules / Battle Conditions
- `towersim/battle_conditions.py` exists, but the Tier BC loader is not yet wired into per-wave stat composition or applied in frozen order.
- Tournament run rules (perks disabled, permanent BCs) not fully wired; perks gate helper exists in `tower_sim/perks_gate.py`.
### Missing (Explicit)
- Tier BC application in per-wave stat composition (loader exists but is not yet integrated).
- Per-wave stat composition (progression + skip mapping not yet feeding stat snapshots).
- Boss combat model (boss-only survivability and death wave estimation).
- Validation harness against Harry’s reference sheets.

### Boss Survivability Model (v1 objective)
- Boss-only combat model (PC + thorns + regen + DR) not implemented.
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
