# Active Workstream

## Project mode
TowerSim is on the **v2 architecture track**.
Do not create v3.
Do not restart from scratch.
Do not maintain parallel active implementations unless explicitly approved.

## Current objective
Move from:
- KB in repo
- IDS ingestion patched
- stage bridge enforced
- staged static outputs materialized

to:
- runtime overlay foundation
- while preserving strict separation between:
  - `baseline_account`
  - `baseline_gem_respec`
  - `baseline_loadout`
  - `runtime_overlay`

## Completed milestones
1. Repo governance/path cleanup completed.
2. Legacy/quarantine area established.
3. IDS compiler fix and hardening/golden tests landed.
4. KB imported into repo in bounded slices.
5. Stage bridge implemented inside existing repo-native contract surfaces.
6. Static staged outputs materialized in existing `static_pipeline_v2`.
7. Contributor-family metadata tightened for staged outputs.

## Current architecture position
The repo now has:
- in-repo KB reference core under `kb/`
- active IDS ingestion path
- v2 stage bridge in native contract surfaces
- deterministic static staged outputs
- fail-closed governance around stage compatibility and family routing
- governed runtime overlay materialization with explicit family ordering

The repo does **not yet** have:
- combat/runtime-state implementation on top of overlays
- evaluator integration against a fully realized runtime overlay system

## Current phase
**Phase: Post-overlay runtime-state execution planning**

Runtime overlay foundation is complete. It delivered the minimum governed runtime overlay layer for:
- perks
- battle conditions
- workshop runtime progression / cash workshop purchases
- free upgrades
- EALS realized effect
- EHLS realized effect

## In scope now
- post-overlay runtime-state execution planning and sequencing
- preserving governed separation between static stages and runtime overlays
- defining the next bounded implementation step without evaluator rewrites

## Out of scope now
- full combat engine implementation in this step
- boss-state execution
- evaluator rewrites
- broad registry redesign
- further broad KB import work
- cosmetic cleanup not needed for architecture

## Hard rules
- Keep using existing repo-native surfaces where possible.
- Extend current pipeline/contracts; do not create parallel systems.
- Fail closed on ambiguous names, stages, or family routing.
- Prefer minimal file sprawl.
- Keep static stages deterministic and unchanged prior to overlay application.


## Phase progress snapshot
- **Completed in this phase:**
  - runtime overlays materialized as a governed layer
  - overlay family ordering and fail-closed validation implemented
  - runtime-state planning surface added (`materialize_runtime_state`) with fail-closed guards
  - deterministic execution semantics stack added (`build_runtime_execution_plan`, `execute_runtime_state_pass`)
  - pre-combat transition/checkpoint/balance-sheet artifacts added with fail-closed consistency checks
  - static-stage baseline audit surface added (`audit_static_stage_baselines`)
  - single composition-root bundle for the execution-semantics phase added (`materialize_runtime_execution_phase_bundle`)
- **Remaining in this phase:**
  - none
- **Status:** execution-semantics phase complete; ready for next bounded pre-combat state mutation slice.


## Immediate next bounded implementation slice (pre-combat state mutation PR-1)
- **Goal:** consume the execution phase bundle and apply deterministic pre-combat state mutations without entering full combat loop/evaluator rewrites.
- **In scope:**
  1. consume `RuntimeExecutionPhaseBundle` as the single validated input surface.
  2. define bounded pre-combat state mutation outputs using ordered transition steps.
  3. preserve fail-closed checks for stage/overlay ordering and transition totals.
- **Out of scope:**
  - boss-state implementation
  - full combat engine loop
  - evaluator migration
  - registry redesign
- **Acceptance checks for PR-1:**
  - bounded pre-combat mutation output exists behind existing repo-native surfaces
  - explicit tests for mutation ordering + fail-closed invalid input cases
  - existing `tests/test_static_pipeline_v2.py` execution-semantics checks remain green

## Success condition for this phase
The repo has a bounded runtime-state planning surface that preserves current separation and proves:
- static stages and runtime overlays remain explicitly separate
- runtime-state assembly keeps static and overlay ordering explicit
- overlay family presence/order validation remains fail-closed
- the next execution-semantic step is scoped without evaluator rewrites
