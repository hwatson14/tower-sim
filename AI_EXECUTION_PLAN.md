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
4. Simulators
5. Optimisers
6. Advisors

### Clarification
- Query Engine answers: what is true now for this account, scenario, and state.
- Simulators answer: what is likely to happen when those truths play out over runtime, timing, and progression.
- Optimisers search and rank.
- Advisors package action guidance.

### Core product surfaces
- Simulator
- Loadout Optimiser
- Progression Optimiser
- Build Transition Advisor

### Product operating principle
TowerSim must feel like one coherent planner, not a bag of isolated calculators or disconnected tools.
Every product surface should read like a different query or decision mode over the same governed lower-layer truth.

### Core product principles
- One optimiser, many queries: avoid inventing separate features when the distinction is really objective, constraint, or horizon selection.
- Keep user questions central: repeated player questions decide whether a surface deserves product attention.
- Explanation is part of the product: recommendations without reasons are incomplete product work.
- Time matters: progression recommendations must account for time-to-earn, not only raw gain.
- Reversibility matters: save/spend and transition advice must consider whether a decision is locked, frictional, or freely adjustable.
- Not every resource deserves equal modelling effort: deepen only the resources that materially change real decisions.
- Module shards and rerolls are separate problems: shards are breakpoint/allocation planning; rerolls are probabilistic target planning.
- Advisors must not become a garbage layer: they summarise, compare, sequence, and explain, but must not hide mechanic invention or bypass lower-layer owners.
- Trust labels matter: every immature or model-governed recommendation surface must expose its confidence class.

### Product-planning distinctions that remain canonical
- Resource = scarce thing earned, spent, allocated, or consumed.
- Domain = sink/system where a resource is invested.
- Progression planning must optimise resources across domains without conflating the two.
- Optimiser families remain distinct: standard ROI/path optimisers, breakpoint/allocation optimisers, and probabilistic target optimisers are not the same planning problem.

### Trust-label taxonomy
Until explicitly replaced by a stronger governed taxonomy, product and planning surfaces should use:
- Canonical
- Strong model
- Accepted model
- Policy heuristic

### Representative user questions by surface
- Simulator: What happens if I run this setup, how far does it go, and what is limiting it?
- Loadout Optimiser: What is my best setup for a stated goal or constraint, and what setup changes explain the win?
- Progression Optimiser: What should I spend next, should I save instead, and what plan best uses my scarce resources over the chosen horizon?
- Build Transition Advisor: When is a build switch realistic, what blocks it, and what path gets there fastest?

### Product scope policy
- True earlier scope should prioritise coins, lab time, and stones as the first progression-resource families.
- Later expansion may add medals, module shards, rerolls, and deeper build-transition planning once lower layers and trust labels are stable.

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
- root R86 docs are retained as historical handoff inputs with Phase 1 obligation mapping now absorbed into this plan
- naming patch/zip artifacts are design inputs only, not direct implementation truth
- root archive artifacts are classified in the Phase 1 archive disposition ledger below
- standalone-roadmap planning truth has now been absorbed into this file; no parallel roadmap remains canonical

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
- explicit absorption note and, if safe, deletion of the standalone roadmap

**Required verification**
- no major doc contradicts canonical layer or phase language
- roadmap content either absorbed or explicitly rejected

**Scope out**
- runtime mechanic changes
- simulator or optimiser implementation

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
- roadmap-only planning truth has been absorbed or explicitly rejected here
- major docs do not contradict the canonical plan
- all root archive artifacts have a documented disposition
- current open obligations are mapped to concrete work items
- control files use the same phase and tranche vocabulary

### Parallelisation rule
Tranches in this phase may run in parallel, but all must be complete before Phase 2 starts.

---

## Phase 1 closeout ledgers

### Phase 1C — R86 obligation closure ledger

| source_doc | source_section | obligation_type | current_status | mapped_phase | mapped_tranche | owner_surface | evidence_or_gap | notes |
|---|---|---|---|---|---|---|---|---|
| `R86_IMPLEMENTATION_SCOPE_AND_ACCEPTANCE.md` | `Tracked status` item 1 | parity evidence | open | Phase 2 | Phase 2E | `AI_EXECUTION_PLAN.md`; future parity matrix outputs | Declared-family parity evidence is still required before Phase 2 can exit. | Keep visible as acceptance evidence, not vague historical open work. |
| `R86_IMPLEMENTATION_SCOPE_AND_ACCEPTANCE.md` | `Tracked status` item 2 | overlay/invalidation closure | open | Phase 2 | Phase 2E | `AI_EXECUTION_PLAN.md`; query-kernel verification surfaces | End-to-end overlay and invalidation evidence remains required. | Bound to declared covered families rather than repo-wide undefined closure. |
| `R86_IMPLEMENTATION_SCOPE_AND_ACCEPTANCE.md` | `Tracked status` item 3 | transitional cleanup | partially_landed_open_tail | Phase 2 | Phase 2A / Phase 2B | `compilers/stat_input_compiler.py`; `engine/progression_recalc_bridge.py` | Bridge path is landed for the bounded runtime/reference path, but residual ownership cleanup still needs explicit function-level classification and approved extraction. | Treat landed bridge work as preserved; do not redo it during ledgering. |
| `R86_IMPLEMENTATION_SCOPE_AND_ACCEPTANCE.md` | `Tracked status` item 4 | benchmark evidence | open | Phase 2 | Phase 2E | `AI_EXECUTION_PLAN.md`; future benchmark evidence outputs | Gate F requires one timing-family and one progression-family benchmark result against the reference path. | Leave open until benchmark evidence is recorded. |
| `R86_IMPLEMENTATION_SCOPE_AND_ACCEPTANCE.md` | `Tracked status` item 5 | ownership extraction | open | Phase 2 | Phase 2A / Phase 2B | `compilers/stat_input_compiler.py`; Query Engine owner surfaces | KB-routing authority extraction is explicitly Phase 2 work. | Starts with the ownership ledger before any seam extraction. |
| `R86_CODEX_HANDOFF_GUARDRAILS.md` | `Hard rules` | preserved_guardrail | active_constraint | Phase 2 | Phase 2A-2E | `AI_EXECUTION_PLAN.md`; affected runtime/code surfaces | Guardrails remain binding implementation constraints until the compiler/query seam work is complete. | They are constraints, not open implementation items by themselves. |
| `R86_CODEX_HANDOFF_GUARDRAILS.md` | `Required worked examples to preserve in code/tests` | preserved_example_obligation | landed_and_preserve | Phase 2 | Phase 2B / Phase 2E | tests and query evidence surfaces | Worked examples remain preserved reference examples for future code/tests. | No rewrite required in Phase 1; preservation remains part of later Query Engine proof. |
| `R86_WORKED_EXAMPLES.md` | all examples | worked_example_reference | landed_reference | Phase 2 | Phase 2B / Phase 2E | `R86_WORKED_EXAMPLES.md`; future tests/docs | Example baseline rows, overlay delta, and query response stay as reference fixtures. | Historical examples retained until stronger query-owned tests supersede them. |

### Phase 1D — Root archive disposition ledger

| artifact | disposition | why | absorbed_into | still_open_items | retirement_condition | merge_as_is_allowed |
|---|---|---|---|---|---|---|
| `towersim_canonical_product_roadmap_v6.md` | absorbed_and_deleted | Remaining useful product-planning truth has been compressed into this plan, so the standalone roadmap no longer adds canonical or necessary historical guidance. | `AI_EXECUTION_PLAN.md` sections on product principles, optimiser families, trust labels, scope policy, and representative user questions. | None. | Retired now; do not recreate a parallel roadmap unless new unique planning truth cannot fit the canonical plan. | no |
| `R86_CODEX_HANDOFF_GUARDRAILS.md` | historical_handoff_reference | Preserves bounded-scope implementation constraints that informed Query Engine work. | Phase 1C ledger in this plan and future Phase 2 execution. | Query Engine ownership completion remains open in Phase 2. | May retire after Phase 2 once all surviving guardrails are either landed or rejected explicitly. | no |
| `R86_IMPLEMENTATION_SCOPE_AND_ACCEPTANCE.md` | historical_handoff_reference | Preserves acceptance framing and tracked status context for the R86 workstream. | Phase 1C ledger in this plan and future Phase 2 tranche outputs. | Phase 2A-2E remain open. | May retire after Phase 2 once every mapped obligation has concrete landed evidence or explicit rejection. | no |
| `R86_WORKED_EXAMPLES.md` | retained_reference_fixture | Still useful as compact human-readable examples for contributor maps, overlays, and query responses. | Future Query Engine tests/docs; referenced by the Phase 1C ledger. | Preserve examples until equivalent or better governed test fixtures exist. | May retire after equivalent governed fixtures are established and referenced from tests/docs. | no |
| `final_naming_contract_reconstruction.patch` | design_input_only | Historical naming reconstruction artifact; not repo truth. | Absorbed naming decisions in `AI_EXECUTION_PLAN.md`, `README.md`, and `ARCHITECTURE.md`. | None. | May retire in Phase 10 once no active document points to legacy naming reconstruction. | no |
| `towersim_merge_candidate_r93_phases1to3.zip` | archive_bundle_do_not_merge | Historical merge candidate bundle; direct merge would bypass tranche and owner-surface governance. | Relevant accepted truth must be re-landed deliberately through current tranche work. | Classify any needed content before retirement if referenced later. | May retire in Phase 10 when confirmed not needed as a historical comparison bundle. | no |
| `module_optimiser_pack14_cumulative_merge_candidate.zip` | archive_bundle_do_not_merge | Historical merge candidate bundle; direct merge would bypass current owner surfaces and review history. | Relevant accepted truth must be re-landed deliberately through current tranche work. | Classify any needed content before retirement if referenced later. | May retire in Phase 10 when confirmed not needed as a historical comparison bundle. | no |
| `els_coin_calc_final_merge_candidate_r94.zip` | archive_bundle_do_not_merge | Historical merge candidate bundle; direct merge would bypass current owner surfaces and review history. | Relevant accepted truth must be re-landed deliberately through current tranche work. | Classify any needed content before retirement if referenced later. | May retire in Phase 10 when confirmed not needed as a historical comparison bundle. | no |

### Phase 1 completion note

Phase 1 is complete when the control stack records: one canonical plan, one active tranche, mapped R86 obligations, documented root-archive dispositions, and no major doc claiming a competing roadmap or layer vocabulary. The standalone roadmap's remaining planning truth is now absorbed here and the file can be retired without losing future product-shaping guidance. The current repo state now meets that bar and promotes execution to Phase 2.

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
- simulator or optimiser work

##### Phase 2C design-only prep ledger

This design note records the Phase 2C manifest population method and the draft family classification that may be prepared in parallel with Phase 2A. It does not imply that Phase 2C is implemented early; it exists so later routing work does not guess about manifest semantics or undelegated fallback ownership.

**Manifest population method**
- The Phase 2C manifest should be generated from governed Query Engine family declarations first, not from ad hoc `resolve_stats()` call sites.
- The source-of-truth seed set is the bounded family list already declared in `kb/global-rules/contracts/stat-query-scenario-families.yaml`.
- The manifest should cross-check each candidate family against `kb/global-rules/contracts/stat-query-initial-surface-set.yaml`, `kb/global-rules/contracts/stat-query-consumer-bundles.yaml`, and the current compatibility entrypoint in `engine/stat_engine.py`.
- Each manifest row must be maintained as an explicit reviewed declaration; later automation may prefill rows from the contracts above, but status fields must remain visible and human-reviewed rather than inferred silently.
- The manifest schema is confirmed to include exactly these governance fields: `family_id`, `delegated_now`, `fallback_owner`, `parity_status`, `benchmark_status`, and `blocker_if_not_delegated`.
- If a family cannot name a fallback owner, the manifest must fail closed and Phase 2C is not complete.

**Status vocab and evidence expectations**
- `parity_status` vocabulary:
  - `not_started`: no parity case or comparison artifact exists yet.
  - `planned`: the family is declared and the intended parity comparison surface set is identified, but no executed evidence is recorded yet.
  - `in_progress`: some parity execution or fixture work exists, but the family does not yet have a complete pass/fail/open disposition.
  - `pass`: declared query surfaces for the family match the compatibility/reference path for the approved comparison scope.
  - `fail`: executed evidence shows a mismatch that blocks treating the delegated family as closed.
  - `blocked`: parity cannot yet be evaluated because ownership or routing truth is still unresolved upstream.
- `benchmark_status` vocabulary:
  - `not_started`: no benchmark plan or result exists yet.
  - `planned`: benchmark scope is named, but no measured run has been recorded.
  - `in_progress`: benchmark harness or capture is underway, but no final disposition exists.
  - `pass`: benchmark evidence for the delegated family has been executed and accepted for the approved workload.
  - `fail`: benchmark evidence shows the delegated path does not yet meet the accepted threshold or exposes a regression.
  - `not_required_yet`: visible placeholder status for undelegated families whose benchmark proof should not be implied prematurely.
  - `blocked`: benchmark work cannot proceed because the owner boundary or delegated path is not yet approved.
- Evidence expectation for Phase 2E:
  - every manifest row must keep the status visible even before evidence exists;
  - `pass` or `fail` requires a cited evidence artifact or test/harness result;
  - `planned`, `in_progress`, and `blocked` require a short bounded note naming the missing proof or dependency;
  - `not_required_yet` is allowed only when `delegated_now` is `false`.

**Draft candidate covered-family list**

Likely delegated-now families:

| family_id | why likely delegated now | fallback_owner | parity_status | benchmark_status | blocker_if_not_delegated |
|---|---|---|---|---|---|
| `timing_tournament_no_perks` | Bounded timing family already declared in scenario-family and initial-surface-set contracts and already exercised by timing query parity tests. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` | `planned` | `planned` | |
| `timing_farm_with_perks` | Same bounded timing family pattern, with governed perks-enabled semantics and existing timing query coverage. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` | `planned` | `planned` | |
| `timing_scenario_probe` | Declared timing family with explicit scenario semantics and bounded query surface ownership. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` | `planned` | `planned` | |
| `progression_runtime_no_perks` | Declared progression runtime family with bounded executor, bridge, overlay, and parity-reference coverage already present. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` | `planned` | `planned` | |
| `progression_runtime_with_perks` | Same as the no-perks runtime family, but with explicit perks-enabled semantics and existing bounded-query coverage. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` | `planned` | `planned` | |

Clearly fallback-owned families:

| family_id | why fallback-owned now | fallback_owner | parity_status | benchmark_status | blocker_if_not_delegated |
|---|---|---|---|---|---|
| `all_other_resolve_stats_outputs` | Any statbook row not owned by a declared family in the Query Engine contracts must remain outside the covered-family manifest for Phase 2C and continue to resolve through the compatibility/reference path. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` | `not_started` | `not_required_yet` | Not a declared Query Engine family yet; Phase 2C must not imply repo-wide delegation. |

Undecided families blocked by ownership ambiguity:

| family_id | why undecided | fallback_owner | parity_status | benchmark_status | blocker_if_not_delegated |
|---|---|---|---|---|---|
| `progression_start_of_run` | Final inclusion is likely, but the manifest should not mark it delegated until Phase 2A confirms that the remaining compiler/query boundary does not leave start-of-run-only routing logic owned by Inputs. | `engine.stat_resolution_core.resolve_stats` via compatibility entrypoint `engine.stat_engine.resolve_stats` | `blocked` if 2A finds unresolved ownership; otherwise `planned` | `blocked` if 2A finds unresolved ownership; otherwise `planned` | Depends on Phase 2A confirming whether start-of-run progression compilation is fully on the Query Engine side of the seam or still partly compiler-owned. |

**2A blocker map for finalizing 2C**
- Phase 2C can draft the manifest structure now, but it cannot finalize any row whose delegated/fallback split still depends on unresolved owner boundaries inside `compilers/stat_input_compiler.py`.
- The highest-risk family is `progression_start_of_run`, because it is declared in Query Engine contracts but may still rely on start-of-run routing or compilation behavior that Phase 2A must classify precisely before 2C can mark it unambiguously delegated.
- The progression runtime families are lower-risk because bridge, overlay, and bounded-executor evidence already point at a query-owned runtime path, but they should still inherit any owner-boundary corrections Phase 2A discovers.
- The timing families are the least ownership-ambiguous because they already compile through dedicated timing-family flows, yet the manifest should still preserve explicit fallback ownership until 2D lands the compatibility-entrypoint routing declaration.
- Any future family not already declared in the bounded family contracts is automatically blocked from manifest inclusion until both of these are true:
  - Phase 2A/2B identify the correct owner boundary for the relevant routing path.
  - a governed Query Engine family declaration exists in the KB contracts.

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

## Phase 7 — Simulator product surfaces

### Purpose
Build the first true simulator product surfaces on top of stable query truth and evaluator substrate.

### Tranches
- Phase 7A — survivability simulator
- Phase 7B — damage-aware run-limit simulator
- Phase 7C — setup comparison simulator
- Phase 7D — richer run-outcome explanation

### Gate to exit Phase 7
All of the following must be true:
- simulator interfaces are consistent
- failure-mode classification is explicit
- run-outcome simulators use governed lower-layer surfaces
- simulator maturity and trust labels are explicit

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
- Phase 10A — remaining archive artifact retirement
- Phase 10B — final pointer cleanup across docs and repo surfaces

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

`input/` must contain an explicit section for user-supplied manual inputs needed by current simulators, optimisers, or advisors.

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
