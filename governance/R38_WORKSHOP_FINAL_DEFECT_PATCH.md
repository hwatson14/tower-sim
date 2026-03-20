# R38 Workshop Final Defect Patch

Closed in this patch:

1. Free upgrade family
   - Free Upgrades card is now split into explicit canonical contributors for attack/defense/utility free-upgrade stats.
   - Free Upgrade Chance for All perk is now also split into those canonicals while preserving the runtime mechanic surface.
   - Phase-3 exact formula now matches the EP/KB shape:
     - (workshop + card + perk + module-substat additive bonuses) x enhancement x relic x vault
   - Shared support row `free_upgrade_multiplier` remains as the enhancement carrier only.

2. Bounce Shot Targets
   - Verified retained as integer-safe publish surface.
   - Current output remains 14 with no fractional published contribution.

3. Max Rend Mult
   - Added canonical `max_rend_mult` surface.
   - Routed workshop Rend Armor Mult into the canonical max-rend formula surface.
   - Routed Max Rend Armor Multiplier lab into the same canonical using explicit 0.25-per-level additive semantics.
   - Routed Max Rend Armor Multi module substat into the canonical surface.
   - Phase-3 exact formula:
     - (8 + lab bonus + module-substat bonus) x workshop rend multiplier

Files changed:
- `compilers/stat_input_compiler.py`
- `engine/stat_engine.py`
- `kb/global-rules/contracts/canonical-stats.yaml`
- `config/destination_formula_ledger.yaml`
- `tests/test_perk_scaling.py`

Verification completed:
- targeted regression tests for free-upgrade split and max-rend exact formula
- full `python run_stats.py --state-mode max_progression --out out_r38_check`
- direct output inspection for free upgrades, bounce targets, and max rend

Known non-blocker observed during broader test-file execution:
- existing perk audit preset-name expectation mismatch in `test_farming_survivability_compare_respects_perk_bans`
- not caused by this patch; left unchanged to avoid unrelated scope drift
