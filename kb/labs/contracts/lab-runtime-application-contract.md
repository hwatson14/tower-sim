# Lab runtime application contract

## Purpose
This contract defines how bundled lab ladders are allowed to participate in simulator-facing stat resolution.

## Active canonical lab surfaces
- `kb/labs/tables/lab-values.csv`
- `kb/labs/tables/lab-track-summary.csv`
- `kb/labs/tables/lab-application-registry.csv`
- `kb/labs/tables/lab-source-registry.csv`
- `kb/labs/tables/wiki-game-speed-lab.csv`
- `kb/labs/tables/module-drop-labs.csv`
- `kb/labs/tables/lab-unresolved-simulator-surfaces.csv`

## Rules
1. `lab-values.csv` is the active numeric ladder surface for bundled generic and wall-related labs.
2. `lab-application-registry.csv` defines where each lab routes in simulator reasoning.
3. A consumer may summarize a ladder from `lab-track-summary.csv`, but must resolve exact numeric level lookups from `lab-values.csv`.
4. A lab may be used in simulation only when its ladder is bundled as an active surface or it is explicitly represented as an external account-state input family.
5. If a simulator-relevant lab is listed in `lab-unresolved-simulator-surfaces.csv`, the model must fail closed and state that the active KB does not yet bundle a source-backed canonical ladder.

## Allowed operations
- multiplicative multipliers for tower or wall stat ladders such as health, regen, and attack speed
- additive percent-point bonuses such as defense percent, recovery package chance, and EALS/EHLS chance
- additive seconds for duration ladders such as Chrono Field duration
- additive wave deltas for wave requirement reduction ladders

## Prohibited behavior
- Do not invent or interpolate a wall fortification curve.
- Do not reinterpret a percent-point ladder as a multiplier.
- Do not override `lab-values.csv` with advisory prose or sourced-but-unsurfaced formulas.
- Do not treat labs researched in one domain as semantic ownership of another domain when the destination stat belongs elsewhere.

## Current packaged closure status
Bundled generic lab ladders are materially closed for active use across the 11 ladder families present in `lab-values.csv`.
The remaining lab-domain simulator gap explicitly tracked in the active package is `LAB_WALL_FORTIFICATION`.
