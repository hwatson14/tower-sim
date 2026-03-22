# AI Migration Execution Plan

## Purpose

This file is the canonical AI-readable execution plan for the current architecture transition.
It is intended to let a new AI session answer, without guessing:

- who owns stat resolution
- where Inputs ownership ends
- where Query Engine preparation begins
- what remains transitional
- what order work should happen in
- what can be parallelised safely
- when root archive artifacts can be retired

This plan is factual to the current repo state and should be updated whenever transition status changes.

---

## Governing truth

### Mechanic truth
- `kb/` is the source of mechanic truth.
- No implementation task may invent mechanics outside KB-backed truth or explicitly governed accepted-model boundaries.

### Ownership truth
- Canonical stat-resolution owner: `engine/stat_resolution_core.py`
- Compatibility-only stat-resolution surface: `engine/stat_engine.py`
- Query Engine owns query-governed published stat surfaces.
- Inputs owns account/input compilation, not final stat resolution.
- Runtime simulators may consume query-owned surfaces but must not re-derive them.
- Analysis/reporting may aggregate truth-owned surfaces but must not replace their owner.

### Current active seam
- `compilers/stat_input_compiler.py` still materially straddles Inputs-owned compilation and Query Engine-owned query preparation.
- The highest-priority refactor seam is finishing that split cleanly.

---

## Current repo-state summary

### Already landed
- Compatibility split between `engine/stat_resolution_core.py` and `engine/stat_engine.py`
- Phase-1 ownership ledger for query-owned surfaces and simulator/runtime consumers
- Family baseline materialisation and query kernel primitives
- Extracted display helpers in `engine/display.py`
- Extracted verification helpers in `engine/verification.py`
- R93 Phase 3 lab tier-list advisory KB artifacts
- Pack14 prep-only KB/contracts/test substrate

### Still open
- One canonical repo-wide migration/status ledger
- Cleanup of ownership wording across all major docs
- Full completion of the `stat_input_compiler.py` seam
- Query-kernel delegation from `resolve_stats()` for covered families
- Declared-family parity closure and benchmark evidence
- Further `run_stats.py` shrink into an orchestrator-first entrypoint
- A governed Inputs-layer lane for manual user-supplied planning/calculation inputs
- New simulator/optimizer/advisor/API layers

### Archive posture
- Root R86 docs remain active references until their open items are absorbed into the migration ledger.
- Naming zip is design input only, not direct implementation truth.
- R93 Phase 3 is materially landed; R93 Phase 1/2 require re-homing into current ownership.
- Pack14 runtime code is not approved for direct merge while its nonruntime draft says proof obligations remain open.
- R94 helper-plane work should be revisited after query ownership and economy-objective work are stable.

### Product roadmap posture
- `towersim_canonical_product_roadmap_v6.md` is an active roadmap input and must be reflected in this execution plan.
- Product-roadmap workstreams are: Estimator, Loadout Optimiser, Progression Optimiser, and Build Transition Advisor.
- These roadmap surfaces map onto the canonical layer stack: Query Engine -> Estimators -> Optimisers -> Advisors.
- The roadmap should be retired to archive only after its active workstreams have been absorbed into this plan and into the canonical migration ledger.

---

### Manual user inputs posture
- `input/` must contain an explicit section for user-supplied manual inputs needed by current estimators, optimisers, or advisors.
- These inputs may cover temporary simplifications before richer evaluators exist and externally observed values that cannot currently be calculated.
- Manual inputs are Inputs-layer artifacts, not KB mechanic truth.
- Each manual input must declare consumer scope, trust label, rationale, and replacement target.
- Once a stronger governed evaluator exists, the corresponding manual input should be retired or marked obsolete.

---

## Execution control system

This repo should be operated with four coordinated control artifacts:

1. `AGENTS.md` for durable repo rules and architectural guardrails
2. `AI_MIGRATION_EXECUTION_PLAN.md` for the canonical full-program map
3. `ACTIVE_TRANCHE.md` for the single active implementation tranche
4. `BURNDOWN.yaml` for machine-readable delivery and verification state

### Operating rule
- The plan is the long-lived program map.
- The active tranche is the only implementation scope Codex should execute right now.
- The burndown is the source of truth for task state, verification state, blockers, and next action.
- Codex should not infer the next task from prose alone when `ACTIVE_TRANCHE.md` and `BURNDOWN.yaml` are present.

---

## Execution principles

1. Do not create a second truth-owning stat engine.
2. Do not let downstream consumers re-derive query-owned surfaces.
3. Prefer the smallest owner-correct change.
4. Preserve deterministic outputs and fail-closed behaviour.
5. Do not merge archived bundles directly if they bypass the current ownership model.
6. Finish ownership truth before broadening feature layers.
7. Treat docs/ledgers as gating infrastructure, not cleanup-only work.

---

## Master phase order

### P0 — Ownership truth and migration ledger
Lock canonical ownership wording and create one authoritative migration/status ledger.

### P1 — R86 closure baseline
Translate root R86 docs into a precise remaining-work baseline. Keep this phase tight: its purpose is to unblock the compiler/query seam quickly, not to become a long documentation tranche.

### P2 — Compiler/query seam completion
Finish separating Inputs-owned compilation from Query Engine-owned query preparation.

### P3 — Resolver delegation
Make query-kernel resolution the canonical path for covered families while preserving compatibility.

### P4 — `run_stats.py` decomposition
Shrink `run_stats.py` into an orchestrator-first entrypoint. Extract only owner-correct cohesive modules. Do not create generic helper sinks or perform aesthetic decomposition ahead of stable ownership.

### P5 — New estimator layer
Build the first estimator surfaces from the product roadmap, starting with survivability and then broadening toward stronger run-outcome estimation.

### P6 — Objective-specific optimisation
Build the roadmap optimiser surfaces, with Loadout Optimiser and Progression Optimiser implemented on top of stable query/estimator inputs.

### P7 — Advisor and external API
Build advisor-layer product surfaces, including progression-planning and build-transition outputs, plus the external query-facing API surface.

### P8 — Archive retirement
Delete root archive artifacts only after their truth has been absorbed or explicitly rejected in the ledger.

---

## Detailed task ledger

### P0-T1 — Lock canonical ownership truth
**Goal**
- Make ownership wording unambiguous across docs and comments.
- Keep `engine/stat_resolution_core.py` as canonical stat-resolution owner.
- Keep `engine/stat_engine.py` compatibility-only.

**Required outputs**
- concise migration note
- aligned wording in `ARCHITECTURE.md`
- aligned wording in `README.md`
- aligned wording in any touched import-facing descriptions

**Done when**
- no major doc implies dual ownership
- compatibility surfaces are named explicitly as compatibility-only
- canonical owner is stated exactly once and reused consistently

**Depends on**
- none

**Parallel with**
- P0-T2

---

### P0-T2 — Create canonical migration/status ledger and control-artifact bootstrap
**Goal**
Create the canonical migration/status ledger and establish the repo-native control artifacts that make it executable.

**Control artifacts included**
- `ACTIVE_TRANCHE.md`
- `BURNDOWN.yaml`

Create one authoritative file describing:
- query-owned
- transitional
- compatibility-only
- parity status
- retirement targets

**Required sections**
- ownership truth
- current open transition items
- covered families and parity status
- unresolved seams
- archive disposition table
- retirement preconditions

**Done when**
- a new AI session can answer ownership/transition questions without guessing
- `ARCHITECTURE.md` and `README.md` point to this ledger
- no major doc contradicts the ledger

**Depends on**
- P0-T1

**Parallel with**
- P1-T1
- P1-T2

---

### P1-T1 — Convert root R86 docs into a precise open-work baseline
**Goal**
Preserve useful R86 constraints while making open items explicit and current.

**Required outputs**
- explicit list of still-open R86 obligations
- explicit list of already-landed R86 obligations
- migration-ledger references replacing ambiguous “R86 complete/incomplete” language

**Done when**
- the repo no longer treats R86 as a vague status bucket
- remaining R86 work is expressed as concrete ledger items

**Depends on**
- P0-T2

**Parallel with**
- P1-T2

---

### P1-T2 — Archive bundle disposition ledger
**Goal**
Classify each root archive as one of:
- landed
- partially landed
- deferred
- rejected
- remap-needed

**Archive targets**
- `R86_CODEX_HANDOFF_GUARDRAILS.md`
- `R86_IMPLEMENTATION_SCOPE_AND_ACCEPTANCE.md`
- `R86_WORKED_EXAMPLES.md`
- `naming_contract_complete_pack_v2.zip`
- `towersim_merge_candidate_r93_phases1to3.zip`
- `module_optimiser_pack14_cumulative_merge_candidate.zip`
- `els_coin_calc_final_merge_candidate_r94.zip`

**Done when**
- each root artifact has a documented disposition
- retirement conditions are explicit

**Depends on**
- P0-T2

**Parallel with**
- P1-T1

---

### P2-T1 — Build function-level ownership ledger for `stat_input_compiler.py`
**Goal**
Classify every function/block as:
- keep in Inputs
- move to Query Engine
- temporarily leave with justification

**Required outputs**
- function-level ownership ledger
- boundary rationale
- identified regression tests for moved behaviour

**Done when**
- no major function remains owner-ambiguous without justification

**Depends on**
- P0-T1
- P0-T2

**Parallel with**
- P4-T1

---

### P2-T2 — Finish extraction of KB routing/query prep from `stat_input_compiler.py`
**Goal**
- Compiler emits raw contributor rows from account state.
- Query Engine owns KB routing, destination binding, value-type binding, stage/composition preparation, and contributor-ledger prep.

**Required outputs**
- cleaner compiler/query boundary
- updated regression coverage
- updated architecture/migration ledger wording

**Done when**
- `stat_input_compiler.py` no longer materially straddles layers in an uncontrolled way
- runtime behaviour is preserved

**Depends on**
- P2-T1

**Parallel with**
- none

---

### P2-T3 — Establish governed manual-advisory input lane under `input/`
**Goal**
Create an explicit Inputs-layer home for user-supplied values required by current calculators, estimators, optimisers, or advisors.

**Examples**
- temporary simplification inputs such as boss damage from orbs
- personal external observations such as weekly gems from perks

**Required outputs**
- input contract/example files under `input/`
- naming guidance for manual input IDs
- trust-label and replacement-target rules
- fail-closed guidance for consumers when a required manual input is absent

**Done when**
- manual user inputs are explicit, scoped, and distinguishable from KB truth
- future evaluators can retire them cleanly via replacement targets

**Depends on**
- P0-T2

**Parallel with**
- P2-T1
- P4-T1

---

### P3-T1 — Delegate covered families from `resolve_stats()` to the query kernel
**Goal**
- Use query-kernel resolution for query-owned covered families.
- Fall back to legacy/core path only for uncovered surfaces.

**Required outputs**
- explicit delegation layer
- family-by-family parity tests
- fallback rules for uncovered families/surfaces

**Done when**
- `resolve_stats()` preserves public API
- covered-family ownership is query-first
- no false suggestion of equal dual ownership remains

**Depends on**
- P2-T2

**Parallel with**
- none

---

### P3-T2 — Close declared-family parity and benchmark evidence
**Goal**
Finish the remaining R86 acceptance evidence for covered families.

**Required outputs**
- parity matrix by family/surface
- benchmark evidence for timing and progression workloads
- migration-ledger status updates

**Done when**
- declared-family coverage has explicit pass/fail/open status
- benchmark evidence is attached to the ledger

**Depends on**
- P3-T1

**Parallel with**
- none

---

### P4-T1 — Decomposition map for `run_stats.py`
**Goal**
Map remaining local concerns into coherent ownership buckets.

**Guardrail**
Extract only owner-correct cohesive modules. Do not create generic helper sinks or perform aesthetic decomposition ahead of stable ownership.

**Likely buckets**
- reporting
- verification leftovers
- gap/audit analysis
- EP comparison plumbing
- orchestration
- output emission

**Done when**
- every remaining major function block has a target owner module or explicit justification for staying in `run_stats.py`

**Depends on**
- P0-T1

**Parallel with**
- P2-T1

---

### P4-T2 — Rewire EP comparison to query responses
**Goal**
Use query responses where possible so comparison rows carry contributor provenance.

**Required outputs**
- query-backed comparison path
- preserved compare payload shape where needed
- contributor-trace availability in reports

**Depends on**
- P3-T1
- P4-T1

**Parallel with**
- P4-T3

---

### P4-T3 — Complete verification extraction
**Goal**
Move remaining cohesive verification/reporting logic out of `run_stats.py`.

**Required outputs**
- verification-owned modules with clear names
- `run_stats.py` slimmer and more orchestration-oriented

**Depends on**
- P4-T1
- P4-T2

**Parallel with**
- P4-T4

---

### P4-T4 — Finish display extraction cleanup
**Goal**
Ensure display formatting remains owned by display-focused helpers.

**Scope note**
This is expected to be a cleanup task, not a greenfield extraction.

**Depends on**
- P4-T1

**Parallel with**
- P4-T3

---

### P5-T1 — Build survivability estimator
**Goal**
Produce the first estimator surface from the product roadmap using query-owned stat truth and wave/runtime engines.

**Outputs**
- waves survived estimate
- failure mode classification
- structured estimator payload
- foundation for stronger run-outcome estimation

**Depends on**
- P3-T1
- P3-T2

**Parallel with**
- P6-T1 design work

---

### P5-T2 — Roadmap estimator expansion plan
**Goal**
Turn the roadmap Estimator surface into an explicit follow-on queue after survivability v1.

**Scope**
- stronger max-wave estimation
- damage-aware run-limit estimation
- setup comparison
- richer run-outcome explanation

**Depends on**
- P5-T1

**Parallel with**
- P6-T1 design work

---

### P6-T1 — Build roadmap optimiser surfaces
**Goal**
Implement the product-roadmap optimiser surfaces:
- Loadout Optimiser
- Progression Optimiser

**Initial optimisation families**
- survivability
- economy
- tournament
- balanced (existing scorer evolves into one objective family among several)

**Depends on**
- P5-T1
- P3-T1

**Parallel with**
- P6-T2

---

### P6-T2 — Re-home archive helper work into owner-correct layers
**Goal**
Decide which archive work to re-home and where.

**Bundle-specific posture**
- R93 Phase 1 thorns: re-home as query/simulator-consumer surface
- R93 Phase 2 ELS BC reduction: re-home as context/query/tournament-support surface
- Pack14: only after ownership stabilises; split KB/query-consumer prep from optimizer logic
- R94: economy/helper-plane candidate under economy-objective work

**Depends on**
- P0-T2
- P3-T1

**Parallel with**
- P6-T1

---

### P7-T1 — Build progression-planning advisor
**Goal**
Create the first Advisor-layer progression-planning surface consuming query, estimator, and optimiser outputs.

**Depends on**
- P5-T1
- P6-T1

**Parallel with**
- P7-T2 schema work
- P7-T3 design work

---

### P7-T2 — Build external query API surface
**Goal**
Expose stable request/response schema for external consumers with contributor traces.

**Depends on**
- P3-T1
- P0-T2

**Parallel with**
- P7-T1

---

### P7-T3 — Build-transition advisor queue
**Goal**
Carry the product-roadmap Build Transition Advisor surface as an explicit advisor workstream rather than leaving it implicit.

**Scope**
- readiness assessment
- gap analysis
- archetype-switch timing
- change-trigger outputs

**Depends on**
- P5-T1
- P6-T1

**Parallel with**
- P7-T1

---

### P8-T1 — Retire root archive artifacts
**Goal**
Delete root docs/zips only after their truth is absorbed or explicitly retired in the ledger.

**Preconditions**
- migration ledger is canonical
- each archive has explicit disposition
- accepted content is landed elsewhere
- major docs point to current truth, not archives

**Depends on**
- P0-T2
- P1-T2
- all accepted archive content resolved

---

## Parallelisation map

### Safe to parallelise immediately
- Track A1: P0-T1 only
- Track A2 after P0-T1: P0-T2 only
- Track A3 after P0-T2: P1-T1 and P1-T2
- Track B after P0-T2: P2-T1 and P4-T1
- Track C design-only: P5-T1 design notes, P6-T1 design notes, P7-T2 schema draft

### Safe to parallelise after P2-T2
- P3-T1 only

### Safe to parallelise after P3-T1 stabilises
- P3-T2
- P4-T2, P4-T3, P4-T4
- P6-T2

### Safe to parallelise after P3-T2 stabilises
- P5-T1
- P6-T1 implementation
- P7-T2 implementation

### Do not parallelise across the same touched owner surfaces
Avoid concurrent ownership-changing edits in:
- `compilers/stat_input_compiler.py`
- `engine/query_routing.py`
- `engine/stat_resolution_core.py`
- `engine/stat_engine.py`
- canonical ownership/migration docs and ledgers

---

## Root archive retirement policy

### Keep for now
- root R86 docs until their open items are absorbed into the migration ledger

### Never merge directly as-is
- naming zip
- Pack14 runtime code zip

### Re-home selectively
- R93 Phase 1/2
- R94 helper-plane tranche

### Keep as active input artifacts
- manual advisory input contract/example files in `input/` until replaced by stronger evaluators

### Safe to retire after provenance is captured
- R93 Phase 3 archive bundle once ledger says it is landed and superseded by in-repo artifacts
- `towersim_canonical_product_roadmap_v6.md` once its active workstreams are fully represented in this plan and the canonical migration ledger

---

## Product roadmap integration

### Roadmap-to-plan mapping
- Roadmap Estimator -> P5-T1 and P5-T2
- Roadmap Loadout Optimiser -> P6-T1
- Roadmap Progression Optimiser -> P2-T3, P6-T1, and P7-T1
- Roadmap Build Transition Advisor -> P7-T3

### Rule
Do not treat the root roadmap as a parallel planning truth once its active workstreams have been absorbed here. At that point it should be archived like the other root transition/reference artifacts.

---

## Success metric

The transition is successful when a new AI session can answer, without guessing:
- who owns stat resolution
- where Inputs ends
- where Query Engine preparation begins
- what `run_stats.py` still owns
- what remains transitional
- what has been retired from root archives

If that cannot be answered from current repo truth plus this plan, the migration is not done.
