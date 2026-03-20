# R30 Count-Add Policy Sweep

## Decision applied
All `count_add` perks now have explicit policy in `kb/perks/tables/perk-effect-registry.csv`.

### No SPB, integer count
- `PERK_ORBS_1`
- `PERK_BOUNCE_SHOT_2`

### SPB applies, integer count
- `PERK_4_MORE_SMART_MISSILES`
- `PERK_1_WAVE_ON_DEATH_WAVE`
- `PERK_EXTRA_SET_OF_INNER_MINES`

## Rationale
- The package already had an explicit exception policy doc for Orbs and Bounce Shot.
- The live wiki standard-perk-bonus formula states additive perks are scaled by SPB generally.
- The three remaining `count_add` perks are still count surfaces, so final emitted values must remain integer.
- Therefore the defensible default is `spb_applies=yes` with `integrality_policy=round_final`.

## What changed
- Added explicit `integrality_policy=round_final` to the three remaining `count_add` rows.
- Left `spb_applies=yes` and `spb_formula_class=additive` in place for those rows.
- Added regression test coverage for the remaining `count_add` rows.

## Known decision point
The current package policy uses integer rounding for count-like standard perks after SPB scaling. If future game evidence shows floor/ceil rather than nearest rounding for any of these three rows, the policy should be revised centrally rather than through one-off code exceptions.
