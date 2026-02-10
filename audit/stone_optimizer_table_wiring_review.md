# Stone Optimizer Table Wiring Review

## Scope and source order
This review follows the requested source order:
1. `tables/`
2. Effective Paths reference artifacts currently available in-repo (`audit/effective_paths_ingest.md`)
3. Open asks for missing source sheets/tables

## What the optimizer currently requires vs what it actually uses
`tower_sim/run/optimizer_engine.py` declares a required stone-table manifest with 7 CSVs, then hard-fails (`fail_closed`) if any are missing. After that gate, `_stone_actions(...)` currently builds actions only from `tables/card_masteries_v1.csv`; UW and assist actions are not implemented yet.

## Table-by-table status

| Table | Present under `tables/` | Wired into action generation | Completeness check | Notes |
|---|---:|---:|---|---|
| `uw_purchase_costs_v1.csv` | ❌ | ❌ | N/A (missing) | Required by manifest only; no loader/action code yet. |
| `uw_track_ladders_v1.csv` | ❌ | ❌ | N/A (missing) | Required by manifest only; no loader/action code yet. |
| `uw_plus_ladders_v1.csv` | ❌ | ❌ | N/A (missing) | Required by manifest only; no loader/action code yet. |
| `assist_slot_unlock_costs_v1.csv` | ❌ | ❌ | N/A (missing) | Required by manifest only; no loader/action code yet. |
| `assist_unique_rarity_upgrade_costs_v1.csv` | ❌ | ❌ | N/A (missing) | Required by manifest only; no loader/action code yet. |
| `assist_efficiency_upgrade_costs_v1.csv` | ❌ | ❌ | N/A (missing) | Required by manifest only; no loader/action code yet. |
| `card_masteries_v1.csv` | ✅ | ✅ | Structurally complete in-file (31 rows; no empty required cells across `card_mastery`, `stone_cost`, `level_0..level_9`) | Only currently wired action source. |

## Effective Paths reference signal (currently available in repo)
From `audit/effective_paths_ingest.md`:
- The workbook snapshot includes `UW Cost Calculator v3` and `DVT_UWs` sheet sections, which indicates extractable UW ladder/cost data exists in reference material.
- I do **not** see an equivalent in-repo extracted section that clearly maps to the 3 missing UW CSVs required by the optimizer manifest.
- I also do **not** see a clear extracted source for the 3 missing assist spend tables in current in-repo reference artifacts.

## Additional wiring/completeness finding
Even for card masteries, one naming mismatch can hide eligible actions:
- Snapshot preset cards include `Recovery Package Chance`.
- `card_masteries_v1.csv` uses `Package Chance`.
- Current `_stone_actions(...)` matches by exact string key, so `Recovery Package Chance` does not produce a mastery action.

## Conclusion
- **Not yet wired:** UW and assist stone spend tables are not wired to optimizer actions.
- **Not yet present in `tables/`:** all 6 non-card required stone spend tables are missing.
- **Currently complete + wired:** only `card_masteries_v1.csv`.
- **Blocking completeness risk:** exact-name mismatch for `Recovery Package Chance` vs `Package Chance`.

## Source request (needed from you)
Please provide one of the following so I can complete the wiring/completeness pass without inventing mechanics:
1. The authoritative CSVs for the six missing files (preferred), or
2. The exact Effective Paths sheet ranges to extract for:
   - UW purchase costs
   - UW track ladders
   - UW+ ladders
   - Assist slot unlock costs
   - Assist unique rarity upgrade costs
   - Assist efficiency upgrade costs

Once provided, I can map them 1:1 into `tables/*.csv` and wire deterministic action generation.
