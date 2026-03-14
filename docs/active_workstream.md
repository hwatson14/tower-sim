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
  - repo-map hygiene blocker removed (`tower_kb_bridge_pack.zip` deleted)
- **Remaining in this phase (bounded planning closure):**
  - none
- **Status:** planning-closure complete; ready for the first execution-semantics implementation PR.


## Immediate next bounded implementation slice (execution semantics PR-1)
- **Goal:** land the first deterministic runtime execution semantics layer on top of `materialize_runtime_state(...)` without evaluator rewrites.
- **In scope:**
  1. define one explicit runtime execution pass that consumes:
     - `start_of_run_stat_values`
     - required runtime overlay families (already ordered)
  2. produce a bounded execution artifact suitable for later combat-state expansion (no full combat loop).
  3. fail closed on missing execution inputs and unexpected execution-phase wiring.
- **Out of scope:**
  - boss-state implementation
  - full combat engine
  - evaluator migration
  - registry redesign
- **Acceptance checks for PR-1:**
  - deterministic execution pass exists behind existing repo-native surfaces
  - explicit tests for execution ordering + fail-closed invalid input cases
  - existing `tests/test_static_pipeline_v2.py` runtime-state/overlay checks remain green

## Success condition for this phase
The repo has a bounded runtime-state planning surface that preserves current separation and proves:
- static stages and runtime overlays remain explicitly separate
- runtime-state assembly keeps static and overlay ordering explicit
- overlay family presence/order validation remains fail-closed
- the next execution-semantic step is scoped without evaluator rewrites
