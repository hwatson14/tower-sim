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
### Data + Snapshot Loading
- `towersim/sources.py` provides snapshot unzip + CSV loading helpers (local snapshot directory model).

### IDS Parsing
- `towersim/ids.py` implements **section splitting** of `_IDS.csv` into named sections.
- **Missing:** typed parsing into a structured `IdsState`.

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

### Wiki Caches + Ingest
- `towersim/wiki/cards.py` reads cached card tables.
- `towersim/wiki/labs.py` + `labs_ingest_all.py` + `labs_formula.py` implement lab value retrieval with formula-first and cache fallback.
- `towersim/wiki/perks.py` provides perk effectiveness helpers.
- `towersim/wiki/labs_eals_ehls.py` provides helpers for EALS/EHLS lab tables.

### Uptime / Wave Time (Partial)
- `towersim/wave_time.py` and `towersim/uptime.py` exist but are not yet validated against authoritative references.

## What is NOT Implemented (Known Gaps)
### Core Architecture Gaps
- Typed `_IDS.csv` → `IdsState` with all required raw fields.
- DataLoader priority order implementation:
  - <24h cache → Git → older snapshot.
  - Git integration is not implemented in the bundled baseline.

### Stat Engine + StatBook
- No unified stat engine that composes:
  Base → Loadout → Enhancements → Tier rules → Derived.
- No StatBook export (`statbook.csv` / `.xlsx`).

### Tier Rules / Battle Conditions
- `towersim/battle_conditions.py` exists, but there is no canonical TierLib applying BCs in the frozen order.
- Tournament run rules (perks disabled, permanent BCs) not fully wired.

### Boss Survivability Model (v1 objective)
- Boss-only combat model (PC + thorns + regen + DR) not implemented.
- No root-find / binary search to find death wave.

### Validation Harness
- No harness comparing outputs to Harry’s reference sheets.

### Optimisers (Later)
- Loadout optimiser and stone spending optimiser not implemented.

## Immediate Next Steps (Codex PR sequence)
1. Implement typed `IdsState` parsing (raw values only) + unit tests.
2. Implement DataLoader priority order (cache/Git/older) + tests.
3. Implement Stat Engine skeleton + StatBook export (no combat) + tests.
4. Wire progression + skip mapping to produce per-wave stats.
5. Implement boss-only combat model and validate against reference sheets.
