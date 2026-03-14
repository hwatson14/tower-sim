# Formula Coverage Audit

This note tracks where the KB has explicit active formula surfaces versus where it only has bundled source traces or partial structured coverage.

## Main conclusion
The package already has active formula/value surfaces for:
- enemy health and damage scaling
- battle-condition curves and heat application
- workshop values and enhancements
- perk pool and module assist ladders
- material combat ordering

The package is still only partial or sourced-not-canonical for:
- some lab curve families
- fully even named per-UW structured ladders across the whole roster
- fully even bot-family structured ladders
- Effective Paths named formulas that remain bundled as evidence but are not all safe to promote directly because the bundled audit itself records blocked issues

## New active surfaces added in v45
- `tables/formula-coverage-ledger.csv`
- `tables/effective-paths-formula-registry.csv`

## Fail-closed rule
Do not promote a sourced formula to active canon merely because it exists in a raw or semi-raw source. Promote only when the formula is internally consistent, does not conflict with active surfaces, and is not flagged by the bundled source audit.
