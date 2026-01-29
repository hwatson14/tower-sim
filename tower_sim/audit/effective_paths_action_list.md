# Effective Paths mechanics consolidation action list

## Purpose
Consolidate mechanics and missing ingestion work from the Effective Paths audits into a single, actionable list.

## Source audits
- `tower_sim/audit/effective_paths_mechanics_comparison.md`
- `tower_sim/audit/effective_paths_formula_comparison.md`
- `tower_sim/audit/effective_paths_ingest.md`

## Consolidated mechanics inventory (by subsystem)

### Modules / Assist efficiency
- **Signals:** `IDS_MOD_GENERATOR_*` tokens in formulas and module sheet helpers.
- **Current coverage:** assist multiplier/substat scaling + aggregation in `tower_sim/modules.py`, `tower_sim/assist_efficiency.py`, and `tower_sim/modules_library.py`.
- **Missing mechanics:** IDS helper mapping for module formulas and module-level lookup logic.

### Workshop / WS+ / Free upgrades
- **Signals:** workshop lookup helpers and Free Upgrade / ELS calculators in Effective Paths formulas.
- **Current coverage:** `_IDS.csv` parsing (WS/WS+) and workshop tables (WSValues/DVT_Workshop) in `tower_sim/libs/workshop_lib.py`; progression simulator in `tower_sim/workshop_progression.py`.
- **Missing mechanics:** Goldbox, ELS/ELS+, coin/ELS ROI calculators; Free Upgrade allocation policy (fail-closed pending authoritative rules).

### Bots
- **Signals:** `DVT_BOT_*`, `IDS_BOT_*`, Golden/Amplify/Thunder path formulas.
- **Current coverage:** none.
- **Missing mechanics:** bot tables + bot path formula ingestion.

### Guardians
- **Signals:** `DVT_GUARDIAN_STAT`, `DVT_GUARDIAN_COST` tokens.
- **Current coverage:** none.
- **Missing mechanics:** guardian stat/cost tables + formulas.

### Ultimate Weapons (UWs)
- **Signals:** `STAT_UW_*`, `EP_*`, `EPC_*`, `EPU_*` tokens and UW DPS formulas.
- **Current coverage:** `_IDS.csv` parsing of UW unlock/track levels.
- **Missing mechanics:** UW stat pipeline and derived stat calculators.

### Laboratory
- **Signals:** lab derived stats and adjusted cost ladders (`LABCOST_SINGLE_ADJUSTED`).
- **Current coverage:** partial lab tables (EALS/EHLS) via wiki cache.
- **Missing mechanics:** full lab ladder ingestion and Effective Paths lab formulas.

### Cards / Relics / Themes & Songs / Player & Stuff
- **Signals:** card multipliers (`EPC_*`), relic/vault helpers (`IDS_RELIC_STAT`, `IDS_VAULT_STAT`), player buffs.
- **Current coverage:** `_IDS.csv` parsing captures state only.
- **Missing mechanics:** derived effects from cards/relics/vault/themes/songs.

### Effective Paths master workbook (v5.00.01)
- **Signals:** dense custom token set (`EPD_*`, `EPH_*`, `EPG_*`, `EPC_*`, `EP_SLM_DPS`, etc.).
- **Current coverage:** base stat engine scaffolding.
- **Missing mechanics:** large portions of stat composition + DPS model chain.

## Action list (one-step increments)
1. **Map custom functions to authoritative sources.**
   - For each token in `tower_sim/audit/effective_paths_formula_comparison.md`, link to a sheet/table or reference. Fail-closed if any token lacks a source.
2. **Extract DVT/IDS tables for bots.**
   - Snapshot `DVT_Bot` + related bot path tables to CSV with provenance notes; add loaders + unit tests.
3. **Extract DVT/IDS tables for guardians.** ✅
   - Snapshot guardian stat/cost tables to CSV with provenance notes; add loaders + unit tests.
4. **Extract UW tables and implement UW stat pipeline.**
   - Snapshot UW ladders to CSV; implement stat composition + derived UW formulas with provenance notes.
5. **Expand lab ladder ingestion.**
   - Capture full lab ladders (including adjusted cost formulas) into CSVs; wire into lab library with tests.
6. **Implement workshop calculators.**
   - Translate Goldbox/ELS/ROI formulas into deterministic code once authoritative formulas are mapped; add tests.
7. **Implement derived card/relic/vault/theme effects.**
   - Map `EPC_*`/`IDS_RELIC_STAT`/`IDS_VAULT_STAT` to authoritative tables and implement stat composition layers.
8. **Integrate Effective Paths master workbook formulas.**
   - Rebuild remaining `EP*` stat chain and DPS calculators with explicit provenance and validation snapshots.
9. **Update validation harness.**
   - Add targeted snapshot checks against sheet outputs for each subsystem as it lands.

## Fail-closed flags (must resolve before mechanics implementation)
- Unmapped custom functions (`DVT_*`, `IDS_*`, `EP*` tokens).
- `COMPUTED_VALUE` placeholders in `_IDS` sheets (requires authoritative definition).
- Free Upgrade allocation policy (workshop progression).
