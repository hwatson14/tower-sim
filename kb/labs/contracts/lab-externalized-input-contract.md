# Lab externalized input contract

## Purpose
This contract defines how simulator consumers must handle lab-linked mechanics that remain explicitly externalized because the package does not bundle an authoritative canonical ladder.

## Active externalized lab inputs
None at present for simulator-critical closed surfaces.

## Rule
When a mechanic is listed in `kb/labs/tables/lab-externalized-simulator-inputs.csv` the simulator may treat the resolved account-instance value as an explicit input surface.

## Required behavior
1. Accept the resolved value only when the surface is explicitly listed as externalized.
2. Keep any externalized input semantically separate from ordinary bundled lab ladders.
3. Record that the value was externally supplied rather than derived from package canon.
4. Preserve fail-closed behavior when a required externalized input is absent.

## Prohibited behavior
- Do not invent or interpolate a missing lab ladder.
- Do not backfill a missing value from advisory text.
- Do not promote an externalized account input into fake global canon.

## Closure note
`LAB_WALL_FORTIFICATION` is no longer externalized. The package now carries the ladder at `kb/labs/tables/wall-lab-wall-fortification.csv`, while the unlock milestone remains source-conflicted and should not affect value application once the lab exists on the account.
