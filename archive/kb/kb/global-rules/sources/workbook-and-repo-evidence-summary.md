# Workbook and Repo Evidence Summary

This note records what the uploaded workbook and internalized source snapshot contributed to KB closure.

## Effective Paths workbook

- Sheets present: `Module Base Stat`, `Data_Val_Tables`, `DVT_Bot`, `All Ultimate Weapons`, `All Bots`, `WSValues`, `DVT_Laboratory`, `DVT_Workshop`.
- These sheets materially support module main effects, Ultimate Weapon and Ultimate Weapon Plus, bots, workshop, and laboratory ladders.

## Internalized tower-sim source snapshot

- Repo input tables provide normalized quantitative surfaces with provenance fields.
- Highest-value tables for KB closure are in `tables/inputs/modules`, `tables/inputs/uw`, `tables/inputs/combat`, and `tables/inputs/tournament`.
- The internalized source snapshot should be treated as a normalization layer, not automatically as canonical truth, because engine/compiler correctness is known to be incomplete.
