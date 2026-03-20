# R40 Free Upgrades and Max Rend audit

This pass was triggered by direct expected-value screenshots.

## Findings before patch
- Free Upgrades card was routed to `canonical_stat::free_upgrade_multiplier` instead of being split across the three chance surfaces.
- Free-upgrade relic rows were being surfaced as fractional values (`0.06`, `0.03`, `0.04`) instead of percentage points (`6`, `3`, `4`) on the chance surfaces.
- Max Rend lab was not visible on the canonical surface in rebuilt outputs, despite intent to route it there.

## Scope of this pass
- Split Free Upgrades card across attack/defense/utility chance surfaces.
- Normalize free-upgrade relic fraction inputs to percentage points on those same surfaces.
- Add hard expected-value tests for farming free-upgrade values and max-rend display value.

## Remaining honesty note
If the free-upgrades expected-value test still fails after the two obvious routing/unit fixes, there is a deeper unresolved contributor or semantic mismatch still present.
