# Progression Engine Merge Notes for AI

## Merge readiness
This bundle is **merge-ready as a progression-engine implementation branch**, not as final mathematically closed gameplay truth.

Merge recommendation: **YES**, with the merge framed as:
- progression engine foundation
- boss-wave v1 progression path
- full safe stat recompute approach
- explicit accepted-model constants and explicit open items retained

Do **not** present the merge as full scenario-closed or final-runtime-complete.

## Scope that is ready to merge
Merge these progression-engine modules and tests:
- `engine/progression_state.py`
- `engine/progression_recalc_bridge.py`
- `engine/perk_timeline_state.py`
- `engine/workshop_progression_policy.py`
- `engine/free_upgrade_generation_policy.py`
- `engine/wave_progression_policy.py`
- `engine/scenario_runtime_inputs.py`
- `engine/boss_wave_engine.py`
- progression tests added for those modules

Also merge the supporting docs under `docs/`, especially:
- `docs/02_engine_architecture.md`
- `docs/05_stat_engine_integration_and_recalc.md`
- `docs/10_workshop_dependency_ledger.md`
- `docs/12_formula_verification_ledger.md`
- `docs/15_engine_readiness_audit.md`
- `docs/16_progression_engine_scope_and_burndown.md`

## What this merge means
After merge, the repo should have:
- IDS-backed progression initialization
- mutable workshop run-state
- safe full stat-engine recompute after run-state changes
- static perk timeline consumption by wave
- deterministic workshop progression support
- deterministic skip-based attack/health-wave policy
- boss TTK slice
- boss damage intake + heat-up slice
- structured scenario-runtime input contract

## What is intentionally still open after merge
These stay open and must remain explicitly labeled as such:
- final scenario-adjusted survivability closure (`WP14b`)
- optimization / partial recompute (`WP15`)
- any stronger replacement for accepted-model constants unless the KB/package supports it

## Accepted-model constants that must remain visible
Do **not** silently upgrade these to wiki-verified unless the KB/package is updated and the docs/tests are updated with it:
- enemy skip warmup / ramp model used by `wave_progression_policy.py`
- deterministic free-upgrade expectation-carry generator

## Merge constraints
1. Do **not** move scenario ownership into progression.
2. Do **not** move perk effect resolution out of the stat engine.
3. Do **not** replace full safe recompute with partial recompute in this merge.
4. Do **not** invent new top-level namespaces if existing package namespaces suffice.
5. Do **not** collapse open items into “done” just because interfaces exist.

## Precedence rules that must be preserved
For runtime combat inputs in progression/boss runtime:
1. governed emitted surface
2. structured scenario runtime input
3. explicit config override
4. accepted baseline fallback where documented

## Recommended merge posture
Use a conservative merge. Prefer retaining explicit comments, notes, and diagnostics rather than “cleaning up” by removing honesty markers.

## Recommended post-merge follow-up
After merge, the next integration step should be to connect the actual scenario-engine outputs into `engine/scenario_runtime_inputs.py` / `engine/boss_wave_engine.py` and then run a focused integration pass.


---

## R75 post-programme handoff pack

This repository also includes a documentation-only post-programme handoff pack under `governance/R75_MERGE_INTEGRATION_AND_ACCEPTANCE_PLAN.md`.

Key rules from that pack:
- treat the guarded incremental runtime line as a stop-point, not a prompt for further uncontrolled DAG expansion
- preserve the no-override rule in stat engine core
- require the guarded-line acceptance tests and benchmark rerun before claiming merge acceptance
- prefer current calculator behavior over stale docs if conflicts appear during future merges

This R75 pack does not itself change runtime behavior.


## R76 merge note
Accepted only the guarded incremental runtime/DAG tranche files, tests, configs, benchmarks, and docs. Rejected candidate regressions to bot canonicals, scenario/timing owners, optimizer timing semantics, and stale stat-engine/compiler surfaces.


## R78 adapted progression-completion merge
- merged progression grouping/dirty-state/scenario-owned progression input fixes
- did not accept raw candidate behavior where it regressed current runtime-contract semantics
- preserved boss runtime governed-surface precedence and tournament league compatibility while merging progression fixes
- next queued item after future merge remains module runtime consumption audit


## R86 pre-Codex tightening pack
Accepted as a selective governance/contracts merge into the active baseline.

Merged in:
- `governance/R86_PRE_CODEX_FREEZE_PACK_TIGHTENING.md`
- `governance/R86_IMPLEMENTATION_SCOPE_AND_ACCEPTANCE.md`
- `governance/R86_CODEX_HANDOFF_GUARDRAILS.md`
- `governance/R86_WORKED_EXAMPLES.md`
- `governance/ITERATION_R86_BURNDOWN.csv`
- `config/stat_query_codex_work_packages.csv`
- `kb/global-rules/contracts/baseline-contributor-map-schema.yaml`
- `kb/global-rules/contracts/overlay-delta-schema.yaml`
- `kb/global-rules/contracts/stat-query-api-contract.yaml`
- `kb/global-rules/contracts/stat-query-initial-surface-set.yaml`
- `kb/global-rules/contracts/stat-query-scenario-families.yaml`
- `kb/global-rules/contracts/stat-query-state-identity.yaml`
- `kb/global-rules/contracts/stat-query-surface-ownership-ledger.yaml`

Merge posture:
- accepted as the current pre-Codex contract pack for the stat-query migration path
- additive governance/control-plane merge, not runtime implementation completion
- preserves existing repo-wide merge notes rather than replacing them with a narrow phase-specific note

Scope/interpretation rules:
- treat these R86 files as active governance/contracts for the stat-query migration path
- do not interpret this merge as proof that the stat-query API or baseline materialiser is already implemented end-to-end
- geometry may exist as a separate scoped subsystem in the repo, but geometry migration remains outside the phase-1 stat-query scope unless later explicitly promoted
- do not create parallel scenario/query contract stacks outside the existing runtime/state contract surfaces
