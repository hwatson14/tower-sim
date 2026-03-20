# R11 Plasma Cannon resolved effect promotion

## Decision
Promote and expose `runtime_mechanic_param::cards.plasma_cannon.effect_pct` as the proper resolved Plasma Cannon effect surface.

## What changed
- Fixed a KB data typo in `kb/cards/tables/card-base-ladders.csv`: `Plasma Canon` -> `Plasma Cannon` for all `PLASMA_CANNON` ladder rows.
- Added runtime mechanic contract entry in `kb/global-rules/contracts/mechanic-params.yaml`:
  - `cards.plasma_cannon.effect_pct`
  - unit: `pct`
  - resolver: `standard_scalar_param`
- Added destination formula ledger entry in `config/destination_formula_ledger.yaml`:
  - `runtime_mechanic_param::cards.plasma_cannon.effect_pct`
  - `formula_class: helper_formula`
  - `publish_policy: allow`
  - `compare_policy: normal`

## Verification
- Regenerated outputs with `python run_stats.py`.
- Verified emitted row exists in `output/statbook_publishable.json`.
- Verified line verification row is `resolved` + `publishable`.
- Verified schema unit is now `pct`.
- Verified formula contract is `helper_formula` rather than `unclassified`.

## Current emitted surface
- destination: `runtime_mechanic_param::cards.plasma_cannon.effect_pct`
- final value: `54.0`
- unit: `pct`
- resolver: `standard_scalar_param`
- formula_class: `helper_formula`
- display_value: `54%`

## Important note
The previous emitted surface was only the boolean capability row. After fixing the ladder-name typo, the calculator now resolves the actual Plasma Cannon effect surface instead. Capability exposure is no longer the primary surfaced row for this mechanic.

## Why this is the right plane
This belongs in the runtime/helper plane, not the top canonical stat plane:
- it is a direct mechanic effect parameter
- it is strategically and optimiser relevant
- it is not a universal top-line tower stat like HP/regen/damage
