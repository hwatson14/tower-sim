# Battle Conditions + Heat: provenance and gaps (v19.0.2)

## What was populated
- `data/tier14_21_battle_conditions.csv`: Tier 14–21 *farming* battle condition magnitudes where explicitly present in the user-provided Notion extract.

## Evidence sources
- Primary for this patch: user-provided Notion extract (assumed derived from Fandom tier pages).
- Secondary to verify: Fandom 'Tiers' and individual BC pages.

## Known gaps (fail-closed intent)
- Tournament heat curves (per league, per wave) are still missing from authoritative sources in the current workspace.
- Many BC magnitudes (e.g., Tier 17–20 Tank/Scatter/Ray/Vampire/Fast/Boss/Basic/Mass Enforcement) are marked MISSING except Tier 21 specifics from the extract.

## Next ingestion step
1. Pull heat curves and the missing BC magnitude tables from the Tower wiki(s) and encode as:
   - `data/heat_wave_scalar.csv` (league,wave,heat_scalar)
   - `data/battle_condition_magnitudes.csv` (league,bc_id,level,parameter,value)
2. Add unit tests that hard-fail if:
   - tournament context requested and heat tables absent
   - a tier references a BC that has no magnitude row
