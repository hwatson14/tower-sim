# Battle Conditions + Heat sources (recovery)

## What this file set represents
- `data/tournament_bc_magnitudes_from_player_and_stuff.csv` is a per-wave (1..1000) tournament battle-condition magnitude table.
- Values were ingested from **Copy of Player & Stuff v3.5.2.xlsx → sheet "Battle Conditions"** using `data_tools/ingest_player_and_stuff_bc.py`.

## Heat representation
This table already varies by wave; it is treated as the *effective* (post-heat) magnitude.
`data/heat_wave_scalar.csv` is currently set to 1.0 for all leagues/waves and is **not** used to derive magnitudes.

## Known ambiguity / conflict to resolve
The Tower wiki indicates:
- Bronze has no heat mechanic (aside from "More Bosses").
- Other leagues have heat that ramps to a maximum at wave 1000.
However, the Player & Stuff sheet provides a single per-wave magnitude curve, and does not expose league-specific scalars.
This workspace therefore **replicates the same curve for all leagues** (fail-closed note: this is an assumption and should be replaced when authoritative league-specific tables are available).

## Next corrective step
Replace league replication with league-specific curves once authoritative numbers are provided (Effective Paths or wiki tables).
