# R08 Helper formula policy and manual closure

## Decision
Helper formulas from EP should remain in the calculator knowledge system even when they are not first-class canonical published stats.

## Policy
Use an explicit helper class for formulas that:
- are useful for optimisation, strategy, validation, or workbook parity
- derive from already-modeled calculator surfaces
- do not need to be emitted as standalone canonical stats today

## Manual closure completed

### EPD_SPB
Classified as `verification_only_helper_or_aggregate`.

Reason:
- SPB is Standard Perk Bonus.
- The package already uses standard perk bonus logic in perk composition.
- EPD_SPB is a helper formula for applying SPB to perk-affected damage-style multipliers, not a standalone canonical output.

### EPD_SHOCKWAVE_DAMAGE
Classified as `verification_only_helper_or_aggregate`.

Reason:
- It is an EP helper derived from ACP tier plus shockwave size/frequency inputs.
- The calculator already models the shockwave inputs and ACP-related mechanics context, but does not currently emit a standalone `shockwave_damage` canonical stat.
- This is better treated as retained helper knowledge for optimisation/strategy/helper outputs than as a missing core stat.

## Recommendation
Later, add an explicit helper-output plane so formulas like these can be emitted deliberately without polluting the canonical stat surface.
