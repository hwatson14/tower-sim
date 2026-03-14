# Workshop runtime contract

## Ownership
Workshop owns permanent and in-run upgrade surfaces for attack, defense and utility.

## Semantics
- Coins fund permanent workshop progress outside a run.
- Cash funds temporary upgrades during a run and resets after the run.
- Free upgrades can trigger after waves and may trigger additional times if Wave Skip resolves.
- Enhancements is a distinct permanent layer and should be modeled separately from base workshop ladders.

## Included tables
- `workshop-values.csv`: base workshop ladders from Effective Paths.
- `enhancements-values.csv`: enhancement ladders / values from Effective Paths.
