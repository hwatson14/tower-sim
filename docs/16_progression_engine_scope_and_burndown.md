# Progression Engine Scope and Burndown

This file is the current execution rail for progression-engine work.

## Scope boundary

In scope now:
- initialize progression from IDS-backed preset workshop levels
- hold mutable workshop run-state
- call full safe stat-engine recompute after run-state changes
- consume fixed perk timeline outputs by wave
- apply explicit workshop progression events by wave
- generate deterministic expected free-upgrade events from emitted chance surfaces
- validate free-upgrade event category against workshop track category
- separate attack wave and health wave
- build boss-wave progression scaffold
- solve boss TTK using governed runtime cadence/effect surfaces when present, with explicit overrides as fallback
- solve baseline boss damage intake with verified +4% heat-up
- keep unresolved cadence/runtime items behind explicit blocked hooks

Explicitly out of scope for the current slice:
- scenario engine implementation
- partial recompute optimisation
- guessed orb/electron cadence rules beyond explicit override contracts
- promotion of missing scenario-derived cadence surfaces into the calculator
- Wave Skip-derived extra free-upgrade generation

## Total work packages

| ID | Work package | Status | Verification status | Notes |
|---|---|---:|---|---|
| WP1 | IDS-backed progression initialization | Complete | Verified | Covered by tests |
| WP2 | Preset to mode/progression mapping | Complete | Verified | Farming/Tourney/Milestone |
| WP3 | Mutable workshop run-state model | Complete | Verified | Current and max level tracked |
| WP4 | Full safe stat recompute bridge | Complete | Verified | No formula duplication in progression |
| WP5 | Workshop override validation | Complete | Verified | Fail-closed bounds checks |
| WP6 | Boss-wave scaffold loop | Complete | Verified | Emits rows honestly with blocked/runtime-ready states |
| WP7 | Emitted surface extraction for boss scaffold | Complete | Verified | Wall, orb, electron, PC, thorns, defense, EALS, EHLS, free-upgrade chance surfaces pulled |
| WP8 | Explicit blocked-item diagnostics | Complete | Verified | No silent assumptions |
| WP9 | Attack-wave progression policy | Complete | Verified (accepted model constant + tests) | Deterministic skip accumulator with accepted warmup model |
| WP10 | Health-wave progression policy | Complete | Verified (accepted model constant + tests) | Same policy, independently applied from EHLS |
| WP11 | Perk timeline consumption by wave | Complete | Verified | Static timeline consumed by wave |
| WP12 | Workshop progression event policy | Complete | Verified | Explicit manual/free-upgrade events by wave |
| WP12a | Free-upgrade source/category validation | Complete | Verified | Fail-closed on category mismatch |
| WP12b | Expected free-upgrade generation from chance pct | Complete | Verified (accepted deterministic model + tests) | Uses expectation carry and stable per-category track-order allocation; excludes Wave Skip extras |
| WP13 | Boss TTK runtime slice with explicit overrides | Complete | Verified | Uses explicit orb pct/cadence, electron cadence, and contact-time overrides |
| WP13a | TTK blocked-state contract for missing overrides | Complete | Verified | Fail-closed until explicit runtime inputs exist |
| WP13b | Governed cadence/effect surface consumption with override fallback | Complete | Verified | Progression now consumes governed boss-runtime surfaces when present and falls back to explicit overrides only where needed |
| WP14 | Boss damage intake + heat-up slice | Complete | Verified | Baseline damage intake now solved from boss base damage, verified +4% heat-up, wall pool, regen, and DR input |
| WP14a | Explicit DR override contract | Complete | Verified | Allows stronger external scenario DR to override baseline tower defense pct |
| WP14b | Final scenario-adjusted damage intake closure | Not started | Open | Scenario engine still needs to provide stronger fixed-for-run DR/overlay surfaces where relevant |
| WP15 | Optimized recompute | Not started | Intentionally deferred | Full safe recompute only for now |

## Verification rules

- Verified means the package contains direct tests, direct emitted surfaces, or KB-backed mechanics sufficient for the current slice.
- Verified (accepted model constant + tests) means the implementation is tested and explicit, but part of the mechanics still relies on an accepted model constant with weaker provenance than wiki-verified rows.
- Blocked means the slice must not guess; it needs either a governed surface, an accepted model constant, or an explicit override contract.

## Current recommendation

Proceed next with:
1. final scenario-adjusted damage intake closure after the scenario engine exists
2. only after that, revisit recompute optimisation
3. optionally promote more governed runtime surfaces to further reduce fallback use

Do not optimize recompute yet.

## Provenance notes

### WP9/WP10 provenance note
- deterministic enemy level skip is KB-backed.
- the specific wave-ramp warmup model remains an **accepted model constant** inside the progression engine until stronger package evidence promotes it.

### WP12b provenance note
- free-upgrade chance surfaces are KB/emitted-stat backed.
- the deterministic expectation-carry generator and stable per-category track-order allocation are an **accepted progression model** for now.
- Wave Skip extra free-upgrade generation is still excluded.


## R10 update

Implemented progression-side scenario interface hardening. The boss runtime can now consume a structured `ScenarioRuntimeInputs` contract for fixed-for-run scenario outputs such as orb boss hit pct, orb cadence, electron cadence, boss contact time, boss hit interval, effective damage reduction, and incoming damage multiplier. Precedence is now: governed statbook/runtime surface first, scenario runtime input second, explicit config override third, accepted baseline last where applicable.
