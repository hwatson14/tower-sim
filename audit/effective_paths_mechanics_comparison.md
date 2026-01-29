# Effective Paths mechanics comparison & ingestion plan

## Scope & sources
- Source sheets: `reference/Effective Paths/*.xlsx`.
- Formula token inventory: `audit/effective_paths_formula_comparison.md`.
- Existing TowerSim mechanics and tables referenced below are in `tower_sim/` and `tests/fixtures/tower-sim-data/`.

## Current extraction status
The formula token inventory captures all custom tokens (IDS/DVT/EP*/STAT_* etc.) observed in each sheet and the count of unique formulas per token. Use this inventory as the canonical list of custom spreadsheet functions/aliases that need mapping into the sim.

## Mechanics comparison (Effective Paths → TowerSim)

### Modules / Assist efficiency
**Effective Paths signals**
- Tokens in sheet formulas include `IDS_MOD_GENERATOR_*` and related module lookup helpers (see token inventory).

**TowerSim coverage**
- Assist main-effect scaling and substat efficiency are implemented in:
  - `tower_sim/modules.py` (assist multiplier formula and substat scaling).
  - `tower_sim/assist_efficiency.py` (assist efficiency aggregation).
  - `tower_sim/modules_library.py` (assist formula helper + module substat definitions).
- Module main effects are intentionally sourced from `_IDS.csv` tables; unique effects/substats are sourced from wiki tables.

**Gap**
- No ingestion for the `IDS_MOD_*` helper functions or module sheet formulas; module-level IDS lookup logic is missing.

### Workshop / WS+ / Free upgrades
**Effective Paths signals**
- Workshop sheet formulas include tokens such as workshop lookup helpers and Free Upgrade / ELS calculators (see token inventory).

**TowerSim coverage**
- `_IDS.csv` parsing for WS/WS+ is in `tower_sim/ids_parser.py`.
- Workshop tables are loaded from `WSValues.csv` and `DVT_Workshop.csv` via `tower_sim/libs/workshop_lib.py`.
- Workshop progression simulator exists but requires an authoritative allocation policy in `tower_sim/workshop_progression.py`.

**Gap**
- Effective Paths calculator formulas (Goldbox, ELS/ELS+, coin/ELS ROI) are not modeled.
- Allocation policy for Free Upgrades remains unspecified and fail-closed.

### Bots
**Effective Paths signals**
- Bots sheet tokens include `DVT_BOT_*` and `IDS_BOT_*` (upgrade tables, cumulative costs, stats).

**TowerSim coverage**
- No bot data loader or mechanics implementation.

**Gap**
- Missing ingestion for bot tables and for bot path formulas (Golden/Amplify/Thunder).

### Guardians
**Effective Paths signals**
- Guardians sheet includes tokens `DVT_GUARDIAN_STAT` and `DVT_GUARDIAN_COST`.

**TowerSim coverage**
- No guardians data loader or mechanics implementation.

**Gap**
- Missing guardian stat/cost tables and formulas.

### Ultimate Weapons (UWs)
**Effective Paths signals**
- UWs sheet includes extensive tokens (`STAT_UW_*`, `EP_*`, `EPC_*`, `EPU_*`, etc.) indicating complex derived stats and DPS calculators.

**TowerSim coverage**
- `_IDS.csv` parsing captures UW unlock/track levels in `tower_sim/ids_parser.py`.

**Gap**
- No UWs stat pipeline or formulas; the UW derived stat calculator is absent.

### Laboratory
**Effective Paths signals**
- Laboratory sheet tokens indicate derived lab stats and adjusted cost ladders (e.g., `LABCOST_SINGLE_ADJUSTED`).

**TowerSim coverage**
- Certain lab tables (EALS/EHLS) are in `tower_sim/wiki` and cache-driven.

**Gap**
- No full lab ladder ingestion for Effective Paths lab formulas and adjusted costs.

### Cards / Relics / Themes & Songs / Player & Stuff
**Effective Paths signals**
- Tokens appear for card-to-workshop multipliers (`EPC_*`), relic/vault lookups (`IDS_RELIC_STAT`, `IDS_VAULT_STAT`), and player buffs.

**TowerSim coverage**
- `_IDS.csv` parsing records card state, relics, vault, and player entries but there is no downstream stat composition for these subsystems yet.

**Gap**
- Derived effects from cards/relics/vault/themes are not modeled.

### Effective Paths v5.00.01 (master workbook)
**Effective Paths signals**
- The main Effective Paths workbook contains the densest custom token set (including `EPD_*`, `EPH_*`, `EPG_*`, `EPC_*`, `EP_SLM_DPS`, and multiple UW-derived stats), implying a full stat-composition and DPS model.

**TowerSim coverage**
- Base stat engine scaffolding exists; many derived stats and DPS calculators are not implemented.

**Gap**
- Missing large portions of the stat composition formulas present in Effective Paths.

## Uncertainties / fail-closed items
- Many formulas rely on custom spreadsheet functions (e.g., `DVT_*`, `IDS_*`, `EP*`) that have no authoritative definition in code or data tables.
- Several sheets use placeholder `COMPUTED_VALUE` outputs instead of explicit formulas, suggesting that some logic is being imported or computed elsewhere.
- Workshop Free Upgrade allocation rules and full UW stat aggregation are not specified in the repo or in the token inventory; these require authoritative sheet formulas or explicit tables.

## Full ingestion & comparison plan
1. **Formalize custom function mapping**
   - For each token in `audit/effective_paths_formula_comparison.md`, map to an authoritative table or formula source.
   - If a token has no explicit formula/table, halt (fail-closed) and request clarification.

2. **Extract tables from Effective Paths**
   - Convert DVT tables (Bots, Guardians, Workshop, UWs, etc.) to CSV snapshots with provenance notes.
   - Store snapshots in `data/` or `tests/fixtures/` with checksum and update provenance in documentation.

3. **Implement ingestion helpers**
   - Add loaders for each new CSV table (bots, guardians, UW ladders, relics, etc.) with unit tests.
   - Wire loaders into the stat engine and into the `_IDS` parsing layer where appropriate.

4. **Rebuild derived stat calculators**
   - Reimplement Effective Paths formula chains in code, keeping a per-formula provenance note.
   - Add unit tests for each derived stat path (e.g., UWs DPS, workshop calculators).

5. **Validation & audit**
   - Update `ARCHITECTURE.md` checklist entries for new ingestion and validation.
   - Add end-to-end checks comparing computed outputs against sheet snapshots.

