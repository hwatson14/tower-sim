# R03 upstream v90 refresh note

## What was ingested
- Upstream calculator: `tower_stat_calc_v90__landmine_and_electron_fix.zip`
- This audit rail remains calculator-first and separate from the parallel implementation naming.

## What changed in upstream package
Upstream added `TAKEOVER_V90_IMPL_FIXES.md`, claiming fixes for:
- `canonical_stat::tower_land_mine_damage`
- `mechanic_param::module.orbital_augment.electron_count`

## What I verified
### Code/package state
- The upstream package regressed the EP mechanics registry back to `ep_v5.00.01_extract_2026-02-02`.
- The upstream package does not contain the explicit `canonical_stat::cash_kill_multiplier` destination policy entry added in this audit rail.
- I re-applied both of those controlled audit-rail fixes.

### Bundled output state
After rerunning `python run_stats.py`, bundled/live outputs still show:
- `canonical_stat::tower_land_mine_damage`: `verification_status = not_resolved`, `final_value = 43.68`
- `mechanic_param::module.orbital_augment.electron_count`: `verification_status = needs_work`, `final_value = null`
- `canonical_stat::cash_kill_multiplier`: still emitted with `formula_contract.formula_class = unclassified`

## Interpretation
There is a package-internal freshness mismatch:
- upstream notes claim the two fixes are complete
- current emitted outputs do not reflect those claimed resolved values

That means I should **not** promote those two surfaces to closed based only on the upstream note.

## Working stance after refresh
- Accept upstream v90 as the latest implementation baseline.
- Keep the two claimed fixes in the **open tail** until emitted outputs or direct code-path proof confirm closure.
- Keep `cash_kill_multiplier` policy entry in config, but treat output hydration as still stale until traced.
- Keep the fresher EP mechanics registry copy-forward in the calculator baseline.

## Live snapshot summary
- publishable surfaces: 175
- needs_work surfaces: 2
- not_resolved surfaces: 3
