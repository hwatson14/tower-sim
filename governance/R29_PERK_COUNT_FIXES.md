# R29 Perk Count Fixes

Implemented fixes:

1. `tower_orb_count` now consumes perk contributors in the destination-specific resolver.
2. Standard Perk Bonus policy is now metadata-driven for perk effects via explicit CSV fields:
   - `spb_applies`
   - `spb_formula_class`
   - `integrality_policy`
3. `count_add` perk effects can now opt out of SPB scaling and enforce integer rounding.
4. Generic `integer_count_stat` resolution now rounds final published values.

Registry updates:
- `PERK_ORBS_1` marked `spb_applies=no`, `spb_formula_class=additive`, `integrality_policy=round_final`
- `PERK_BOUNCE_SHOT_2` marked `spb_applies=no`, `spb_formula_class=additive`, `integrality_policy=round_final`
- other additive and multiplicative standard perk effects received explicit default metadata rows for future wiring.

Verification snapshot:
- `canonical_stat::tower_orb_count` now publishes `8`
- `canonical_stat::tower_bounce_shot_targets` now publishes `14`
- targeted perk regression tests pass
- `python run_stats.py` passes

Important note:
- `tower_bounce_shot_targets = 14` is consistent with package data if workshop contributes `8` and `Bounce Shot +2` has quantity `3` for a total perk add of `6`.
- any expectation of `16` implies either a different workshop base or a different perk quantity/value assumption and should be treated as a separate mechanics/data question.
