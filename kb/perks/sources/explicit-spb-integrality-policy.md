# Explicit SPB and Integrality Policy for Count-Like Perks

This note makes explicit several perk-effect policies that were previously implicit in registry interpretation.

## Standard Perk Bonus applicability

### Count-like additive perks that do **not** receive SPB scaling
- `PERK_ORBS_1` (`Orbs +1`): additive count perk, integer result, no SPB scaling
- `PERK_BOUNCE_SHOT_2` (`Bounce Shot +2`): additive count perk, integer result, no SPB scaling

### Additive perk that **does** receive SPB scaling
- `PERK_INCREASE_MAX_GAME_SPEED_BY_1_00` (`Increase Max Game Speed by +1.00`): additive non-integer perk, SPB applies

### Multiplicative perk that uses multiplicative SPB formula
- `PERK_X1_15_DEFENSE_ABSOLUTE` (`x1.15 Defense Absolute`): multiplicative standard perk, SPB applies via multiplicative standard-perk formula

## Integrality policy

### `round_final`
Used for count-like resolved surfaces where the final published stat must be integer.
- `PERK_ORBS_1`
- `PERK_BOUNCE_SHOT_2`

### `none`
Used for non-integer additive or multiplicative perks where the final value is not integer constrained.
- `PERK_INCREASE_MAX_GAME_SPEED_BY_1_00`
- `PERK_X1_15_DEFENSE_ABSOLUTE`

This document is mirrored into the perk CSV registries through explicit fields:
- `spb_applies`
- `spb_formula_class`
- `integrality_policy`
