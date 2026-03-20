# R61 Bot Unlock And Module Unique Coverage

This tranche closes two calculator-contract gaps:

1. Bot canonicals now honor ownership via `capability::bot.<name>.owned` in the stat engine.
2. All 24 module unique scalar effects now have canonical `mechanic_param::module.*` outputs plus contributor mappings, with a coverage regression test to prevent silent drift.

Important distinction:
- "wired to canonical output" does not mean every module unique is already consumed by downstream runtime engines.
- The canonical/stat-engine ownership layer is now present for all 24 scalar effects.
