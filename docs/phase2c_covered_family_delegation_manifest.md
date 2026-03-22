# Phase 2C — Covered-family delegation manifest

Change classification: **Cleanup only**.

## Scope note

This manifest finalizes the governed covered-family list for Phase 2C using the bounded family declarations in `kb/global-rules/contracts/stat-query-scenario-families.yaml`, the declared surface registry in `kb/global-rules/contracts/stat-query-initial-surface-set.yaml`, the bounded consumer declarations in `kb/global-rules/contracts/stat-query-consumer-bundles.yaml`, and the public compatibility entrypoint exported by `engine/stat_engine.py`.

It is a governance artifact for delegation scope only. It does **not** imply that `engine.stat_engine.resolve_stats` already delegates every listed family through the query kernel, and it does **not** imply full repo-wide Query Engine ownership for undeclared `resolve_stats()` outputs.

## Governing rules applied

- Only family IDs already declared in `kb/global-rules/contracts/stat-query-scenario-families.yaml` are eligible for Phase 2C manifest rows.
- Every undelegated or partially governed area must name an explicit fallback owner.
- Undeclared `resolve_stats()` outputs remain outside covered-family delegation and continue through the compatibility/reference path until a future governed family declaration exists.
- Parity and benchmark status stay visible even when evidence is still planned, blocked, or not yet required.
- `progression_start_of_run` must remain visibly bounded so the manifest does not imply that all progression-family routing is already delegated end to end.

## Covered-family manifest

| family_id | delegated_now | delegated_scope | fallback_owner | parity_status | benchmark_status | blocker_if_not_delegated |
| --- | --- | --- | --- | --- | --- | --- |
| `timing_tournament_no_perks` | `true` | Query-governed timing family declared in the scenario-family contract, surfaced in the initial surface set, and already consumed through bounded timing query bundles. Delegation is governed only for the declared timing-family surfaces and overlays, not for unrelated `resolve_stats()` outputs. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` for any surface outside the family contracts or any undeclared compatibility-only output. | `planned` | `planned` | |
| `timing_farm_with_perks` | `true` | Query-governed timing family with explicit perks-enabled semantics, bounded initial surfaces, and bounded timing consumer bundles. Delegation remains limited to the declared timing-family contract surface set. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` for any surface outside the family contracts or any undeclared compatibility-only output. | `planned` | `planned` | |
| `timing_scenario_probe` | `true` | Query-governed timing probe family with explicit scenario semantics and bounded initial surfaces/consumer bundles. Delegation is limited to the declared timing probe surface set rather than all probe-adjacent runtime helpers. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` for any surface outside the family contracts or any undeclared compatibility-only output. | `planned` | `planned` | |
| `progression_runtime_no_perks` | `true` | Query-governed progression runtime family declared in the scenario-family contract and bounded by the initial surface set and progression runtime consumer bundles. Delegation is limited to the declared runtime progression surfaces and runtime-approved overlays only. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` for any surface outside the family contracts or any undeclared compatibility-only output. | `planned` | `planned` | |
| `progression_runtime_with_perks` | `true` | Query-governed progression runtime family with explicit perks-enabled semantics, bounded declared surfaces, and bounded runtime consumer bundles. Delegation remains limited to the declared runtime progression surfaces and approved perk-enabled overlays. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` for any surface outside the family contracts or any undeclared compatibility-only output. | `planned` | `planned` | |
| `progression_start_of_run` | `false` | Declared progression family with governed surfaces and bounded consumer references, but start-of-run coverage remains bounded to the declared contract surface set and must not be treated as implicit proof that the full start-of-run routing path is already delegated through the query kernel. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` | `planned` | `not_required_yet` | Start-of-run progression remains contract-declared, but Phase 2C keeps it fallback-owned until later routing work explicitly proves the public compatibility path delegates this family without implying broader full-delegation coverage. |
| `all_other_resolve_stats_outputs` | `false` | Not a declared Query Engine family. This catch-all row exists only to make non-covered compatibility outputs visible and bounded; it is explicitly outside covered-family delegation. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` | `not_started` | `not_required_yet` | Not eligible for delegation in Phase 2C because no governed Query Engine family declaration exists for the remaining compatibility-only output space. |

## Family-by-family review notes

### Delegated-now families

The delegated-now set is limited to the three timing families and the two progression runtime families. Those five families are the only Phase 2C rows marked `delegated_now: true` because they are all already declared in the scenario-family contract and bounded by both the initial surface registry and consumer-bundle contracts. This keeps delegation explicit and prevents any implied claim that undeclared or non-family `resolve_stats()` behavior is already query-owned.

### Explicitly bounded undelegated family

`progression_start_of_run` remains in the manifest as an explicit undelegated family instead of being omitted. Keeping the row visible makes the open area governed and bounded: the family is recognized, its fallback owner is named, and its parity/benchmark status is visible without overstating current routing coverage.

### Explicit fallback-only remainder

`all_other_resolve_stats_outputs` is intentionally retained as a fallback-only row so the manifest does not imply full `resolve_stats()` delegation. This row is not a new Query Engine family and does not expand coverage; it makes the undeclared remainder visible so Phase 2D can preserve an explicit compatibility fallback path and Phase 2E can avoid claiming evidence for outputs outside the governed family set.

## Status posture for Phase 2E handoff

- `planned` parity status means the family has a governed target comparison surface but no completed Phase 2E evidence artifact is recorded yet.
- `planned` benchmark status means the family is expected to receive benchmark evidence once the delegated public path is exercised and measured in Phase 2E.
- `not_required_yet` benchmark status is used only for undelegated rows so the manifest does not falsely imply benchmark obligations were already met for fallback-owned paths.
- No family is marked `pass` or `fail` yet because this tranche defines the governed target surface; it does not claim completed parity or benchmark execution.

## Completion check

- [x] Finalized the covered-family list from the governed family declarations already present in KB contracts.
- [x] Made delegated scope explicit for each declared covered family.
- [x] Named the fallback owner for every undelegated or out-of-scope area.
- [x] Kept undelegated areas visible and bounded without implying full delegation.
- [x] Recorded parity and benchmark status for every manifest row so Phase 2E has a governed target surface.
