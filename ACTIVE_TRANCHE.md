# ACTIVE_TRANCHE

## Tranche ID
`PH2-TRANCHE-E_COVERED_FAMILY_PARITY_AND_BENCHMARK_EVIDENCE`

## Phase
`Phase 2 — Query Engine ownership completion`

## Objective
Record covered-family parity and delegated-workload benchmark evidence without implying repo-wide delegation closure or hiding bounded open work.

## Scope in
- parity matrix by manifest family and relevant surface
- benchmark evidence tied only to currently delegated compatibility workloads
- explicit pass/fail/open recording for unresolved families
- Phase 2 exit-gate review against recorded evidence

## Scope out
- new family coverage beyond the Phase 2C manifest
- formula rewrites
- new delegation implementation beyond already-landed routing
- simulator or optimiser changes

## Required outputs
- parity evidence matrix
- delegated-workload benchmark capture
- explicit pass/fail/open status note
- Phase 2 exit-gate check

## Required verification
- every manifest family has a visible evidence status
- delegated-workload benchmark evidence is bounded to real delegated compatibility paths
- unresolved families remain visibly bounded instead of being reported as vague partial progress
- the Phase 2 exit-gate decision is explicit

## Acceptance criteria
- every manifest row has explicit parity and benchmark status
- benchmark evidence is attached only to currently delegated workloads
- open failures and blockers are named explicitly
- phase-exit readiness is stated plainly

## Blockers
- none

## Stop conditions
Stop once parity and benchmark evidence are recorded for every manifest family, delegated benchmark capture is attached only to real delegated workloads, and the Phase 2 exit-gate outcome is explicit.

## Non-goals
- do not expand the covered-family manifest
- do not treat undelegated query-family parity as proof of compatibility-entrypoint delegation
- do not hide benchmark failures or open blockers behind partial wording

## Folded residue conclusions

### Phase 2A compiler ownership ledger
- `compilers/stat_input_compiler.py` remains the compatibility entrypoint for stat-input row assembly, account-state decoding, preset selection, and value materialization.
- Query Engine ownership applies to state-mode publication policy, perk query semantics, and query-routing registry loaders.
- Inputs ownership remains with source-family value materialization and row-construction helpers that still support the compatibility entrypoint.
- Risky ownership changes stay anchored by `tests/test_state_mode_contracts.py`, `tests/test_perk_scaling.py`, `tests/test_r86_completion.py`, `tests/test_smoke.py`, and `tests/test_bot_module_uniques_and_unlocks.py`.

### Phase 2B compiler/query boundary rationale
- `compilers/stat_input_compiler.py` still owns row creation, account-state decoding, preset selection, and value materialization.
- Query Engine ownership now covers state-mode contract loading/filtering, perk-selection semantics, and routing registries that prepare published query-facing surfaces.
- Boundary-preservation regressions remain anchored by `tests/test_state_mode_contracts.py`, `tests/test_perk_scaling.py`, and `tests/test_r86_completion.py`.

### Phase 2C covered-family delegation manifest

| family_id | delegated_now | delegated_scope | fallback_owner | parity_status | benchmark_status | blocker_if_not_delegated |
| --- | --- | --- | --- | --- | --- | --- |
| `timing_tournament_no_perks` | `true` | Declared timing-family surfaces and overlays only. | `engine.stat_resolution_core.resolve_stats` via `engine.stat_engine.resolve_stats` for anything outside the family contracts or undeclared compatibility-only outputs. | `pass` | `fail` | Delegated compatibility parity is bounded and passing, but the delegated benchmark currently fails against the fallback/reference path. |
| `timing_farm_with_perks` | `true` | Declared perks-enabled timing-family surfaces only. | `engine.stat_resolution_core.resolve_stats` via `engine.stat_engine.resolve_stats` for anything outside the family contracts or undeclared compatibility-only outputs. | `in_progress` | `blocked` | Query-family parity exists, but compatibility-entrypoint delegation is still ambiguous for this family so delegated benchmark capture remains blocked. |
| `timing_scenario_probe` | `true` | Declared timing probe surfaces only. | `engine.stat_resolution_core.resolve_stats` via `engine.stat_engine.resolve_stats` for anything outside the family contracts or undeclared compatibility-only outputs. | `in_progress` | `blocked` | Declared timing-surface parity exists, but compatibility-entrypoint delegation has not landed for this family yet. |
| `progression_runtime_no_perks` | `true` | Declared runtime progression surfaces and approved overlays only. | `engine.stat_resolution_core.resolve_stats` via `engine.stat_engine.resolve_stats` for anything outside the family contracts or undeclared compatibility-only outputs. | `in_progress` | `blocked` | Query-family parity exists, but progression rows still stay on the explicit compatibility fallback path so delegated benchmark capture is blocked. |
| `progression_runtime_with_perks` | `true` | Declared runtime progression surfaces and approved perk-enabled overlays only. | `engine.stat_resolution_core.resolve_stats` via `engine.stat_engine.resolve_stats` for anything outside the family contracts or undeclared compatibility-only outputs. | `in_progress` | `blocked` | Query-family parity exists, but compatibility-entrypoint delegation has not landed for this family yet. |
| `progression_start_of_run` | `false` | Declared progression family remains bounded to the contract surface set and is not yet proof of delegated start-of-run routing. | `engine.stat_resolution_core.resolve_stats` via `engine.stat_engine.resolve_stats` | `blocked` | `not_required_yet` | Keep this family fallback-owned until later routing work proves start-of-run delegation explicitly. |
| `all_other_resolve_stats_outputs` | `false` | Explicit non-family fallback remainder only. | `engine.stat_resolution_core.resolve_stats` via `engine.stat_engine.resolve_stats` | `not_started` | `not_required_yet` | No governed Query Engine family declaration exists for the remaining compatibility-only output space. |

### Phase 2E parity and benchmark evidence

| family_id | delegated_now | query-family surface parity | compatibility-entrypoint parity | delegated benchmark evidence | explicit status | bounded evidence / blocker |
| --- | --- | --- | --- | --- | --- | --- |
| `timing_tournament_no_perks` | `true` | `pass` | `pass` | `fail` | `open` | Delegated surfaces match direct query-kernel output, but the 2026-03-22 delegated benchmark remains slower than the fallback/reference path. |
| `timing_farm_with_perks` | `true` | `pass` | `open` | `open` | `open` | Query helper parity is covered, but `resolve_stats()` still keeps this family on the explicit fallback path. |
| `timing_scenario_probe` | `true` | `pass` | `open` | `open` | `open` | Declared timing surfaces still match the canonical stat engine, but compatibility-entrypoint delegation is not implemented for this family yet. |
| `progression_runtime_no_perks` | `true` | `pass` | `open` | `open` | `open` | Progression helper and support-surface parity are covered, but compatibility-path delegation remains open. |
| `progression_runtime_with_perks` | `true` | `pass` | `open` | `open` | `open` | Query helper and support-surface parity are covered, but compatibility-entrypoint delegation has not landed for this family yet. |
| `progression_start_of_run` | `false` | `open` | `open` | `open` | `open` | This row remains intentionally undelegated and fallback-owned until later routing work proves delegation explicitly. |
| `all_other_resolve_stats_outputs` | `false` | `open` | `open` | `open` | `open` | This row remains the explicit non-family fallback remainder. |

Benchmark capture retained for the only currently delegated compatibility workload on 2026-03-22:
- `resolve_stats()` delegated compatibility path median: `7891.412 ms`
- `engine.stat_resolution_core.resolve_stats()` fallback reference median: `32.311 ms`
- direct `StatQueryKernel.resolve_surfaces()` median: `0.185 ms`

Phase 2 exit-gate posture retained from the folded evidence: seam ambiguity removed, manifest current, delegation explicit, parity visible, benchmark evidence present, compatibility entrypoint preserved, and no major doc implies dual ownership. The current gate outcome remains **ready to exit** under the governed Phase 2 definition.
