# Lab externalized input contract

## Purpose
This contract defines how simulator consumers must handle lab-linked mechanics that are acknowledged by the package but do not have a bundled source-backed level ladder in active canon.

## Active externalized lab input
- `LAB_WALL_FORTIFICATION` -> `wall_fortification_bonus_pct`

## Rule
When a mechanic is listed in `kb/labs/tables/lab-externalized-simulator-inputs.csv` the simulator may treat the resolved account-instance value as an explicit input surface.

## Required behavior
1. Accept the resolved value only when supplied by a parser snapshot, account-state export, or direct user input.
2. Keep the input semantically separate from ordinary bundled lab ladders.
3. Record that the value was externally supplied rather than derived from package canon.
4. Preserve fail-closed behavior when the external input is absent.

## Prohibited behavior
- Do not derive Wall Fortification from guessed linear steps.
- Do not backfill a missing fortification value from advisory text.
- Do not promote an externalized account input into a fake global ladder.

## Closure note
This contract closes the simulator-use pathway for Wall Fortification without inventing a bundled research curve that the package does not actually contain.
