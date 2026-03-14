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

The repo does **not yet** have:
- runtime overlay materialization as a governed execution layer
- combat/runtime-state implementation on top of overlays
- evaluator integration against a fully realized runtime overlay system

## Current phase
**Phase: Runtime overlay foundation**

This phase should add the minimum governed runtime overlay layer for:
- perks
- battle conditions
- workshop runtime progression / cash workshop purchases
- free upgrades
- EALS realized effect
- EHLS realized effect

## In scope now
- runtime overlay materialization layer
- overlay-family routing and validation
- overlay separation from static stages
- tests for overlay presence, ordering, and fail-closed behavior

## Out of scope now
- full combat engine implementation
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

## Success condition for this phase
The repo can materialize runtime overlays as a distinct layer, with tests proving:
- static stages remain stable before overlays
- overlays are separate and governed
- overlay ordering is explicit
- incompatible or missing overlay inputs fail closed
