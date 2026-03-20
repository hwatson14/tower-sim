# R59 Combat Runtime Contract Tranche

## Purpose
Promote boss-runtime input resolution into the timing engine so progression stops owning ad hoc precedence and so defensible combat-runtime surfaces can be closed centrally.

## What changed
- Added `CombatRuntimeSurfaces` and `resolve_combat_runtime_surfaces(...)` to `engine/timing_engine.py`.
- Rewired `engine/boss_wave_engine.py` to consume timing-owned combat runtime surfaces.
- Closed `orb_boss_hit_pct` from account state via KB table `kb/global-rules/tables/note-derived-orb-boss-hit-levels-1-10.csv` when a governed runtime row is absent.

## Ownership after patch
- `scenario_engine.py`
  - owns scenario/world surfaces only.
- `timing_engine.py`
  - owns temporal surfaces and combat-runtime input resolution order.
- `boss_wave_engine.py`
  - consumes resolved combat-runtime surfaces; no longer owns precedence logic for orb pct/cadence/contact/DR.

## Closed surface
### Orb Boss Hit percent
Resolved by precedence:
1. governed runtime surface row
2. account-state lab level `Orb Boss Hit` via KB level->pct table
3. scenario runtime input
4. explicit override

This closes a real defended mechanic surface without inventing stat-engine routing that is not yet present.

## Remaining open surfaces
The following remain intentionally open in the current package because there is no defended formula in the repo KB/package:
- orb boss-hit cadence
- electron hits per second
- boss contact time seconds

These are now timing-engine-owned open gaps rather than boss-wave-engine-owned scattered fallbacks.

## Why this is correct
- It improves correctness where the KB is sufficient.
- It avoids inventing fake cadence/contact formulas.
- It moves the unresolved contract into the correct owner so later closure happens once, not in every consumer.

## Next tranche
Close the remaining combat-runtime gaps only after a defended contract exists for:
- orb boss-hit cadence
- OA electron cadence / speed
- boss contact timing
