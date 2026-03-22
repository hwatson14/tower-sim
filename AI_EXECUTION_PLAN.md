# AI_EXECUTION_PLAN.md

## Purpose

This is the canonical AI-readable execution plan for the repo.

It replaces the old split between:
- migration plan
- standalone product roadmap

It is intended to let a new AI session answer, without guessing:
- what the repo is
- what the canonical layer model is
- what workstreams exist
- what must be finished before later work starts
- what can run in parallel inside a phase
- what the current and future product surfaces are
- what proof is required before advancing

This file is the long-lived whole-program map.
`ACTIVE_TRANCHE.md` defines the only work Codex should execute right now.
`BURNDOWN.yaml` is the machine-readable state and verification ledger.

---

## Operating rule

This plan is phase-gated.

That means:
- all tranches inside a phase may run in parallel when they do not touch the same owner surfaces
- no tranche from the next phase should begin until the current phase is complete and verified
- later phases may be designed early, but not implemented early
- if a phase gate is not met, stop and resolve it before continuing

This is the core execution rule.

---

## Governing truth

### Mechanic truth
- `kb/` is the source of mechanic truth.
- No implementation task may invent mechanics outside KB-backed truth or explicitly governed accepted-model boundaries.

### Ownership truth
- Canonical stat-resolution owner: `engine/stat_resolution_core.py`
- Compatibility-only stat-resolution surface: `engine/stat_engine.py`
- Query Engine owns query-governed published stat and objective surfaces.
- Inputs owns account/input compilation, not final stat resolution.
- Simulators and evaluators may consume query-owned surfaces but must not re-derive them.
- Optimisers and advisors may aggregate truth-owned surfaces but must not replace their owners.

### Current active seams
- `compilers/stat_input_compiler.py` still materially straddles Inputs-owned compilation and Query Engine-owned query preparation.
- `run_stats.py` still contains orchestration plus embedded verification, reporting, and comparison concerns.
- eHP, eDamage, and eEcon are still effectively optimiser-local rather than fully query-owned objective surfaces.
- verification and testing are not yet structured as first-class program workstreams.

---

## Canonical architecture and product model

### Layer stack
1. Knowledge Base
2. Inputs
3. Query Engine
4. Estimators
5. Optimisers
6. Advisors

### Clarification
- Query Engine answers: what is true now for this account, scenario, and state.
- Simulators are runtime or event-model components used beneath estimator surfaces.
- Estimators are the forecast surfaces built from Query Engine truth plus simulator logic.
- Optimisers search and rank.
- Advisors package action guidance.

### Core product surfaces
- Estimator
- Loadout Optimiser
- Progression Optimiser
- Build Transition Advisor

### Immediate architectural rule
Do not expand product surfaces on top of unstable ownership boundaries.

---

## Current repo-state summary

### Already landed
- Compatibility split between `engine/stat_resolution_core.py` and `engine/stat_engine.py`
- family baseline materialisation and query-kernel primitives
- extracted display helpers
- extracted verification helpers
- governed manual-input lane concept
- strong KB base and active runtime core

### Still open
- canonical archive and R86 disposition closure
- full `stat_input_compiler.py` seam completion
- query-kernel delegation for covered families
- parity and benchmark closure for delegated families
- objective-state promotion for eHP, eDamage, and eEcon
- verification substrate for surfaces and evaluators
- structured evaluator foundation, especially max-wave evaluation
- test-lane redesign and speed improvements
- further `run_stats.py` decomposition
- broader product-surface implementation

### Archive posture
- root R86 docs remain active references until absorbed into this plan and ledger
- naming zip is design input only, not direct implementation truth
- archive bundles must be classified before retirement
- the old standalone roadmap should be removed once fully absorbed here

---

## Program workstreams

The repo now has six primary workstreams:

1. Ownership and archive closure
2. Query Engine completion
3. Objective-state promotion
4. Verification and evaluator foundation
5. Test and CI acceleration
6. Product surfaces

These are governed by the phase order below.

---

## Master phase order

## Phase 1 — Canonical planning truth and archive closure

### Purpose
Create one clean, current, canonical planning truth and close legacy ambiguity before deeper implementation continues.

### Why this phase exists
The repo still has archive-driven ambiguity and overlapping planning truth.

### Tranches
- Phase 1A — Control-stack closeout and tranche promotion
- Phase 1B — Canonical plan and terminology unification
- Phase 1C — R86 obligation closure ledger
- Phase 1D — Archive disposition ledger
- Phase 1E — Control-stack alignment (`ACTIVE_TRANCHE.md`, `BURNDOWN.yaml`, doc pointers)

### Tranche requirements

#### Phase 1A — Control-stack closeout and tranche promotion
**Goal**
- Close or explicitly supersede the current bootstrap control tranche.
- Align active control truth to this execution-plan model.

**Required outputs**
- control-stack closeout note
- explicit bootstrap status: completed, superseded, or blocked
- first promoted tranche ID under the new phase-gated system

**Required verification**
- current active tranche acceptance criteria checked
- control-file naming and references reviewed
- stale IDs identified or removed

**Scope out**
- runtime mechanic changes
- Query Engine code changes
- product feature implementation

#### Phase 1B — Canonical plan and terminology unification
**Goal**
- Unify naming across major docs.

**Required outputs**
- one canonical execution-plan file
- aligned terminology in major docs
- explicit removal or retirement note for the standalone roadmap

**Required verification**
- no major doc contradicts canonical layer or phase language
- roadmap content either absorbed or explicitly rejected

**Scope out**
- runtime mechanic changes
- estimator or optimiser implementation

#### Phase 1C — R86 obligation closure ledger
**Goal**
- Convert legacy R86 material into concrete current work items.

**Required output schema**
- `source_doc`
- `source_section`
- `obligation_type`
- `current_status`
- `mapped_phase`
- `mapped_tranche`
- `owner_surface`
- `evidence_or_gap`
- `notes`

**Required verification**
- every still-relevant R86 obligation is mapped
- already-landed items are separated from open items
- vague “R86 complete/incomplete” wording is removed

**Scope out**
- direct code changes
- archive merges

#### Phase 1D — Archive disposition ledger
**Goal**
- Classify each root artifact and state exactly what happens to it.

**Required output schema**
- `artifact`
- `disposition`
- `why`
- `absorbed_into`
- `still_open_items`
- `retirement_condition`
- `merge_as_is_allowed`

**Required verification**
- each root artifact has one disposition only
- retirement conditions are explicit
- direct-merge-forbidden artifacts are named

**Scope out**
- archive content implementation
- runtime feature work

#### Phase 1E — Control-stack alignment
**Goal**
- Align `ACTIVE_TRANCHE.md`, `BURNDOWN.yaml`, and major doc pointers to the new plan.

**Required outputs**
- updated active tranche
- updated burndown
- updated doc references

**Required verification**
- phase and tranche IDs are consistent
- no stale plan filename remains
- control files point to canonical truth

**Scope out**
- future phase implementation work

### Gate to exit Phase 1
All of the following must be true:
- bootstrap tranche is closed or explicitly superseded
- one canonical plan exists and is current
- roadmap content has been absorbed here
- major docs do not contradict the canonical plan
- all root archive artifacts have a documented disposition
- current open obligations are mapped to concrete work items
- control files use the same phase and tranche vocabulary

### Parallelisation rule
Tranches in this phase may run in parallel, but all must be complete before Phase 2 starts.

---

## Phase 2 — Query Engine ownership completion

### Purpose
Finish the Inputs ↔ Query Engine boundary and establish stable query-owned family resolution.

### Why this phase exists
No later work should build on an unstable core stat-resolution boundary.

### Tranches
- Phase 2A — `stat_input_compiler.py` function-level ownership ledger
- Phase 2B — Compiler/query seam extraction
- Phase 2C — Covered-family delegation manifest
- Phase 2D — `resolve_stats()` delegation to query kernel
- Phase 2E — Covered-family parity and benchmark evidence

### Tranche requirements

#### Phase 2A — `stat_input_compiler.py` function-level ownership ledger
**Goal**
- Classify every meaningful unit in `stat_input_compiler.py` by owner and action.

**Required output schema**
- `unit_id`
- `unit_type`
- `source_lines`
- `current_owner`
- `target_owner`
- `action`
- `justification`
- `target_module`
- `test_anchor`
- `move_now_or_later`

**Action values**
- `keep`
- `move`
- `split`
- `temporary_stay`

**Required verification**
- no major unit remains unclassified
- every `move` or `split` has a destination
- risky moves identify regression anchors

**Scope out**
- code edits
- formula rewrites
- opportunistic cleanup

#### Phase 2B — Compiler/query seam extraction
**Goal**
- Move only the approved Query Engine-owned seam from the compiler into its proper owner.

**Required outputs**
- extracted owner-correct code changes
- updated boundary rationale
- updated regression coverage

**Required verification**
- runtime behaviour preserved
- moved behaviour covered by targeted tests
- docs updated for the new boundary

**Explicit non-goals**
- no `StatInput` schema redesign
- no formula rewrites
- no generic helper sink creation
- no unrelated engine cleanup
- no new fallback behaviour unless already specified by manifest or contract

#### Phase 2C — Covered-family delegation manifest
**Goal**
- Make delegation scope explicit before broader routing changes continue.

**Required output schema**
- `family_id`
- `delegated_now`
- `fallback_owner`
- `parity_status`
- `benchmark_status`
- `blocker_if_not_delegated`

**Required verification**
- covered-family scope is explicit
- fallback owner is named for every undelegated family
- parity and benchmark status are visible

**Scope out**
- unrelated family expansion
- estimator or optimiser work

#### Phase 2D — `resolve_stats()` delegation to query kernel
**Goal**
- Route declared covered families through the query kernel while preserving the public compatibility entrypoint.

**Required outputs**
- explicit delegation path
- fallback path for undelegated families
- public entrypoint preserved

**Required verification**
- declared covered families delegate through the query kernel
- undelegated families still resolve via explicit fallback
- no false implication of full delegation

**Scope out**
- new family coverage beyond manifest
- run_stats decomposition

#### Phase 2E — Covered-family parity and benchmark evidence
**Goal**
- Prove the delegated path is valid for declared families.

**Required outputs**
- parity matrix by family and surface
- benchmark evidence for delegated workloads
- explicit pass, fail, or open status

**Required verification**
- every manifest family has evidence status
- benchmark scope is attached to declared delegated families
- open failures are visible and bounded

**Scope out**
- new mechanic work
- product-surface expansion

### Gate to exit Phase 2
All of the following must be true:
- the compiler/query seam is no longer materially owner-ambiguous
- covered-family delegation is explicit and governed
- covered-family manifest exists and is current
- parity status exists by declared family and surface
- benchmark evidence exists for the delegated path
- the public compatibility entrypoint remains preserved
- no major doc implies dual ownership

### Parallelisation rule
Phase 2A may run with design work for 2C.
Phase 2B, 2C, 2D, and 2E may partially overlap where safe, but Phase 2 is not complete until all are complete and verified.

---

## Phase 3 — Objective-state promotion

### Purpose
Promote core composite objective surfaces into Query Engine truth instead of leaving them optimiser-local.

### Why this phase exists
eHP, eDamage, and eEcon are important enough to be first-class governed surfaces.

### Objective surfaces in scope
- `objective_state::ehp`
- `objective_state::edamage`
- `objective_state::eecon`

### Tranches
- Phase 3A — Objective-state contracts and maturity ledger
- Phase 3B — eHP promotion to Query Engine surface
- Phase 3C — eDamage promotion to Query Engine surface
- Phase 3D — eEcon promotion to Query Engine surface
- Phase 3E — Optimiser rewire to consume query-owned objective states
- Phase 3F — Objective-state parity and accepted-model evidence

### Gate to exit Phase 3
All of the following must be true:
- all three objective states have declared owners and query surfaces
- optimiser does not own the canonical formulas anymore
- maturity labels and known-gap statements are explicit
- parity or accepted-model evidence exists per objective state
- contributor-trace expectations are defined for each objective surface

### Parallelisation rule
3B, 3C, and 3D may run in parallel after 3A.
3E may begin once the relevant promoted surfaces are stable.
3F closes the phase and must cover all three objective states.

---

## Phase 4 — Verification and evaluator foundation

### Purpose
Make verification a first-class system and establish the governed evaluator substrate, starting with max-wave evaluation.

### Why this phase exists
The repo needs a proof system before broader product expansion.

### Tranches
- Phase 4A — Surface verification registry
- Phase 4B — Evaluator contract framework
- Phase 4C — Max-wave evaluator reference corpus
- Phase 4D — Max-wave evaluator implementation or hardening
- Phase 4E — Evaluator verification matrix
- Phase 4F — Query-backed comparison and verification extraction from `run_stats.py`

### Verification classes
- surface verification
- evaluator verification
- system verification

### Gate to exit Phase 4
All of the following must be true:
- governed verification registries exist
- max-wave evaluator inputs, outputs, and assumptions are explicit
- a reference corpus exists for max-wave verification
- evaluator verification status is visible by case family
- comparison and verification responsibilities are less embedded in `run_stats.py`

### Parallelisation rule
4A and 4B may run in parallel.
4C may begin once 4B is stable.
4D and 4F may overlap where surfaces are stable.
4E closes the phase.

---

## Phase 5 — Test and CI acceleration

### Purpose
Make the repo fast enough and reliable enough for iterative Codex work.

### Why this phase exists
The current marker model is only a starting point; the repo needs explicit test lanes and measured speed improvements.

### Tranches
- Phase 5A — Test inventory and timing profile
- Phase 5B — Test lane redesign
- Phase 5C — Fixture and artifact strategy cleanup
- Phase 5D — Default fast suite and heavy-suite separation
- Phase 5E — CI and benchmark policy alignment

### Target test lanes
- unit_fast
- contract
- parity
- evaluator
- integration
- benchmark

### Gate to exit Phase 5
All of the following must be true:
- test lanes are explicitly defined
- default developer-fast validation path exists
- heavy proof suites are separated from default runs
- timing bottlenecks are known and addressed at least for top offenders
- CI policy matches the lane model

### Parallelisation rule
5A should happen first.
5B, 5C, and 5D may run in parallel after 5A.
5E closes the phase.

---

## Phase 6 — `run_stats.py` decomposition and thin orchestration

### Purpose
Shrink `run_stats.py` only after the core owners, objective surfaces, verification model, and test system are stable enough.

### Why this phase exists
Earlier decomposition risks moving unstable boundaries.

### Tranches
- Phase 6A — `run_stats.py` decomposition map
- Phase 6B — reporting extraction
- Phase 6C — verification and comparison extraction cleanup
- Phase 6D — output emission and orchestration cleanup

### Gate to exit Phase 6
All of the following must be true:
- every major remaining concern in `run_stats.py` has a target owner
- extracted modules have clear ownership
- `run_stats.py` is primarily orchestration
- outputs remain stable and validated

### Parallelisation rule
6A must happen first.
6B, 6C, and 6D may partially overlap after 6A.

---

## Phase 7 — Estimator product surfaces

### Purpose
Build the first true estimator surfaces on top of stable query truth and evaluator substrate.

### Tranches
- Phase 7A — survivability estimator
- Phase 7B — damage-aware run-limit estimator
- Phase 7C — setup comparison estimator
- Phase 7D — richer run-outcome explanation

### Gate to exit Phase 7
All of the following must be true:
- estimator interfaces are consistent
- failure-mode classification is explicit
- run-outcome estimators use governed lower-layer surfaces
- estimator maturity and trust labels are explicit

### Parallelisation rule
7A should land first.
7B, 7C, and 7D may follow in parallel where dependencies permit.

---

## Phase 8 — Optimiser product surfaces

### Purpose
Build stable optimiser families on top of query-owned objective states and verified evaluators.

### Tranches
- Phase 8A — loadout optimiser
- Phase 8B — progression optimiser core
- Phase 8C — resource-family optimiser expansion
- Phase 8D — save-vs-spend and branching logic
- Phase 8E — archive helper re-homing where justified

### Gate to exit Phase 8
All of the following must be true:
- optimisers consume stable lower-layer surfaces
- objective families are explicit
- recommendation confidence and trust logic is visible
- save-vs-spend branching is governed, not ad hoc

### Parallelisation rule
8A and 8B may run in parallel once the lower phases are complete.
8C and 8D may overlap later.
8E is selective and should only occur where ownership is already stable.

---

## Phase 9 — Advisor surfaces and external interfaces

### Purpose
Build the user-facing planning and strategy surfaces after the lower stack is trustworthy.

### Tranches
- Phase 9A — progression-planning advisor
- Phase 9B — build-transition advisor
- Phase 9C — external query and API schema
- Phase 9D — advisor explanation and trust-label packaging

### Gate to exit Phase 9
All of the following must be true:
- advisor outputs consume governed lower layers
- strategy explanations are traceable to model outputs and KB knowledge
- external interfaces expose stable schema
- trust labels remain explicit

### Parallelisation rule
9A, 9B, and 9C may run in parallel where safe.
9D closes the phase.

---

## Phase 10 — Archive retirement and cleanup closure

### Purpose
Retire superseded root artifacts only after their truth has been absorbed or explicitly rejected.

### Tranches
- Phase 10A — roadmap retirement
- Phase 10B — archive artifact retirement
- Phase 10C — final pointer cleanup across docs and repo surfaces

### Gate to exit Phase 10
All of the following must be true:
- no active work depends on retired root artifacts
- all retained truths are represented in canonical in-repo sources
- repo docs point to current truth, not legacy bundles

---

## Detailed tranche ledger

Each tranche should carry:
- goal
- scope in
- scope out
- touched owner surfaces
- forbidden surfaces
- required outputs
- required verification
- blockers
- stop conditions

This detail belongs in `ACTIVE_TRANCHE.md` and `BURNDOWN.yaml`, not repeated exhaustively here.

---

## Phase dependencies summary

- Phase 1 must finish before Phase 2 starts
- Phase 2 must finish before Phase 3 starts
- Phase 3 must finish before Phase 4 starts
- Phase 4 must finish before Phase 5 starts
- Phase 5 must finish before Phase 6 starts
- Phase 6 must finish before Phase 7 starts
- Phase 7 must finish before Phase 8 starts
- Phase 8 must finish before Phase 9 starts
- Phase 9 must finish before Phase 10 starts

This sequence is mandatory unless the plan itself is explicitly revised.

---

## Parallelisation rules

### General rule
Parallelise tranches only when they do not change the same owner surfaces or invalidate each other’s proof.

### Never parallelise ownership-changing edits across the same surfaces
Examples:
- `compilers/stat_input_compiler.py`
- `engine/stat_resolution_core.py`
- `engine/stat_engine.py`
- query contracts and delegation manifests
- canonical plan and control files when changing IDs or gates

### Design can precede implementation
A later phase may be designed early, but not implemented early.

---

## Manual user inputs posture

`input/` must contain an explicit section for user-supplied manual inputs needed by current estimators, optimisers, or advisors.

These inputs:
- are Inputs-layer artifacts
- are not KB mechanic truth
- must declare consumer scope
- must declare trust label
- must declare rationale
- must declare replacement target
- must fail closed where required

This remains active until replaced by stronger governed evaluators.

---

## Success metric

The program is successful when a new AI session can answer, without guessing:
- what layer owns a given surface
- what phase the repo is in
- what must be complete before the next phase starts
- what work may run in parallel right now
- whether eHP, eDamage, and eEcon are query-owned
- how verification and evaluator truth are governed
- how testing is structured
- what legacy artifacts have been retired

If that cannot be answered from repo truth plus this file, the execution system is not complete.
