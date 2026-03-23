# Optimizer objective-surface posture

## Phase 3 status

The optimizer no longer owns canonical eHP, eDamage, or eEcon formulas. It consumes the Query Engine-published derived objective surfaces instead:

- `derived::ehp`
- `derived::edamage`
- `derived::eecon`

## Failure policy

If a required derived objective surface is missing, the optimizer fails closed rather than re-deriving the value locally.

## Remaining Phase 3 gap

This consumption boundary is in place, but full Phase 3 closeout still depends on broader runtime validation and parity/accepted-model evidence for the promoted surfaces.
