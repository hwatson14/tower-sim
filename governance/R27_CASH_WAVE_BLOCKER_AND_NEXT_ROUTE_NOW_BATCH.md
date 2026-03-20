# R27 Cash / Wave blocker and next route-now batch

## Outcome
`Cash / Wave` remains **open** as a lab-routing defect.

This is **not** another alias-normalization problem.
The prior vault alias issue was closed in R26. The remaining raw row is the **lab** track.

## What was verified

The package currently contains:
- workshop `cash_per_wave` routing and value surface
- vault alias routing to `canonical_stat::cash_per_wave`
- perk routing to `canonical_stat::cash_per_wave`

The package does **not** currently contain a packaged lab surface for `Cash / Wave` in any of the lab control tables:
- `kb/labs/tables/lab-application-registry.csv`
- `kb/labs/tables/lab-track-summary.csv`
- `kb/labs/tables/lab-values.csv`

Therefore the remaining raw row is not safely closable from the current package.

## Why I did not patch it

Binding the lab row directly to `canonical_stat::cash_per_wave` without a packaged lab value surface would keep the input as a raw level contributor, which is exactly the failure mode the harness is trying to catch.

That would make the ledger cleaner while making the calculator less truthful.

## Required closure condition

To close `Cash / Wave` correctly, the package needs at least one of:
1. a lab application registry row plus a validated ladder in `lab-values.csv`, or
2. a lab application registry row plus a trustworthy linear summary in `lab-track-summary.csv`, or
3. an explicit package-level accepted formula entry for the lab track.

Until one of those exists, this defect should remain open and classified as `route_bind_needs_ladder_or_formula`.

## Next route-now batch status

A refreshed scan of the remaining blocked route-now lab defects shows the same pattern for most of them: the destination may be conceptually known, but the package does not yet ship the lab routing and numeric ladder surfaces needed for safe binding.

See `R27_REMAINING_ROUTE_NOW_BLOCKERS.csv` for the exact blocker ledger.
