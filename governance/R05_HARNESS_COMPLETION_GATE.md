# R05 harness completion gate

## Verdict
- **Verdict:** usable_with_caveats_not_fully_complete
- **Meaning:** the calculator's in-scope publishable surface set is strong enough to continue as the trusted baseline for this audit rail, but the package is **not** fully complete as a universal publish-everything calculator.

## Why this is the correct verdict
- **In-scope calculator mapping:** 293/293 inputs mapped (100.0%).
- **Resolved emitted rows:** 171/364.
- **Publishable rows:** 161.
- **Blocked rows:** 10.
- **EP true formula mismatches:** 0.
- **Blocked formula contracts:** 0.

## Gate interpretation
### What passed
- Calculator-scope inputs are fully mapped for the intended current calculator scope.
- Regenerated canonical outputs close the prior open tail for `tower_land_mine_damage`, `module.orbital_augment.electron_count`, and `cash_kill_multiplier` classification.
- EP comparison currently shows **zero true formula mismatches** on the compared set.
- Remaining blocked compare rows are all **stage-scope mismatches**, not demonstrated live arithmetic defects.

### What prevents a stronger completion verdict
- `output/diagnostics.json` still marks overall `publish_status` as `forbidden_for_publish`.
- 193 rows are still trace-only / unmapped in emitted output because the package intentionally retains surfaces outside the current calculator publish scope.
- 195 active unmapped inputs remain in diagnostics, mostly lab/admin or intentionally excluded rows; these are governance boundaries, not proof of broken calculator math.
- 335 emitted rows still carry `formula_class: unclassified` in `output/statbook_publishable.json`; this is a governance maturity gap even where values are correctly resolved.
- 10 EP compare rows remain blocked due to stage-scope mismatch against EP's max-progression/max-workshop/run-perk assumptions.

## Recommendation
Use this refreshed baseline as the continuing calculator canon for the audit rail.
Do **not** claim “fully complete package” yet.
The right stronger claim is:

> **Calculator-scope publishable surfaces are operationally usable and internally consistent on regenerated output, with remaining incompleteness concentrated in scope-excluded inputs, governance classification coverage, and EP stage-context mismatches.**

## Highest-value remaining work
1. Fresh contributor-led closure on `tower_hp` under the regenerated baseline.
2. Reconcile `tower_damage` compare-runtime assumptions with frozen compare policy.
3. Decide whether to expand formula-contract classification beyond the currently promoted/validated subset.
4. Define optimiser interface only from trusted resolved publishable outputs.
