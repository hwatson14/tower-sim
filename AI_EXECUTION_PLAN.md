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

**Phase 4 authority reset — in effect from Phase 4 entry:**
- Query Engine (bounded API: `engine/stat_query_kernel.py`, `engine/family_baseline_materializer.py`, `engine/state_identity.py`) is the sole canonical execution path for new Phase 4 stat-resolution work.
- `engine/stat_resolution_core.py` is **legacy/reference-only**. It was the pre-Phase-4 canonical stat-resolution owner and is being vacated under Phase 4. No new canonical stat logic may be added to it.
- `engine/stat_engine.py` is a thin compatibility entrypoint only. It is not a canonical implementation target for new work.
- New Phase 4 implementation work must target QE-owned paths. Adding logic to `stat_resolution_core.py` or `stat_engine.py` is a scope violation unless explicitly authorised as a compatibility shim.

**Pre-Phase-4 baseline (migration context only):**
- Pre-Phase-4 canonical stat-resolution owner: `engine/stat_resolution_core.py` (being vacated)
- Compatibility-only stat-resolution surface: `engine/stat_engine.py`

**Layer ownership (all phases):**
- Query Engine owns query-governed published stat and objective surfaces.
- Inputs owns account/input compilation, not final stat resolution.
- Simulators and evaluators may consume query-owned surfaces but must not re-derive them.
- Optimisers and advisors may aggregate truth-owned surfaces but must not replace their owners.

### Naming reset — Phase 4 entry

`state::` and `runtime_mechanic_param::` naming patterns are migration-era/legacy aliasing. They are not the canonical naming target for new Phase 4 work.

New Phase 4 work must:
- Target the current canonical QE naming surface and/or a governed alias contract.
- Not silently expand old `state::` or `runtime_mechanic_param::` naming patterns.

If a legacy naming pattern must be bridged for backward compatibility, that bridge must be declared explicitly in the alias contract, not inlined silently into new implementation work.

The live instance of this rule is the timing-family naming mismatch: `state::cards.wave_accelerator.spawn_rate_acceleration` does not align with `runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration`. This is an open blocker for PH4-B, not implied coverage. It must be resolved explicitly, not worked around.

Handoff documents (`PH4A_CANONICAL_MIGRATION_LEDGER.md`, `PH4A_FAMILY_ENTRY_MATRIX.md`) are handoff artifacts, not canonical merged-control truth, unless explicitly promoted into a control file.

### Legacy-surface rule after Phase 4
If `engine/stat_engine.py` and/or `engine/stat_resolution_core.py` remain after Phase 4, they remain only as:
- thin compatibility entrypoints, and/or
- non-canonical legacy merge/reference aids for reconciling work built from older baselines.

They must not:
- be named canonical owners of stat-resolution truth
- receive new canonical stat logic
- become routing destinations for new stat surfaces entering scope

### Current active seams
- `compilers/stat_input_compiler.py` still materially straddles Inputs-owned compilation and Query Engine-owned query preparation.
- `run_stats.py` still contains orchestration plus embedded verification, reporting, and comparison concerns.
- eHP, eDamage, and eEcon are now query-owned derived objective surfaces; the remaining open work is governed verification and evaluator layering on top of them.
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
- Query Engine-owned promotion of `derived::ehp`, `derived::edamage`, and `derived::eecon` with bounded Phase 3 closeout evidence
- strong KB base and active runtime core

### Still open
- full `stat_input_compiler.py` seam completion
- query-kernel delegation for covered families
- parity and benchmark closure for delegated families
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

The repo now has ten primary workstreams:

1. Ownership and archive closure
2. Query Engine completion
3. Objective-state promotion
4. Full stat-resolution migration to Query Engine
5. Verification, evaluator foundation, and test acceleration
6. `run_stats.py` decomposition and thin orchestration
7. Simulator product surfaces
8. Optimiser product surfaces
9. Advisor surfaces and external interfaces
10. Archive retirement and cleanup closure

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

Implementation evidence now lives in `ACTIVE_TRANCHE.md`. The design-only prep ledger below remains as planning history, but the governed Phase 2C target surface is the folded active-tranche record.

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

##### Phase 2C design-only prep ledger (historical prep notes)

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
Record the completed promotion of core composite objective surfaces into Query Engine truth so later phases can build verification and evaluator work on top of them.

### Why this phase exists
eHP, eDamage, and eEcon were important enough to require promotion into first-class governed surfaces; this phase is now complete and remains here as the historical plan record for that promotion.

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

### Resource-income implementation timing
Resource-income surfaces requested for optimiser and evaluator consumption should be scheduled as lower-layer economy truth rather than deferred as a product-only optimiser feature.

#### Phase 3D scope expansion — resource-income query surfaces
Phase 3D should include the governed promotion work for deterministic per-resource income surfaces that underpin `objective_state::eecon`.

Required work inside 3D:
- define KB-backed income semantics, units, and supported-resource boundaries for each resource surface promoted now
- add query-owned resource-income surfaces for every deterministically calculable resource
- mark non-deterministic or advisory-only resources as explicitly unsupported rather than inferred
- make `objective_state::eecon` consume those governed surfaces instead of leaving canonical economy ownership in optimiser code

#### Phase 3E follow-on — optimiser consumption
Once the relevant 3D surfaces are stable, 3E should rewire optimiser consumers to read the query-owned resource-income/eEcon surfaces instead of re-deriving canonical economy truth locally.

#### Phase 4 evaluator timing
Evaluator consumption of resource-income surfaces should begin only in Phase 4, after evaluator contracts and verification exist:
- 4B defines evaluator inputs and assumptions for resource-income consumption
- 4D implements or hardens evaluator paths against the query-owned surfaces
- 4E records verification status by evaluator family/case

#### Phase 8C product expansion boundary
Phase 8C remains the right place for resource-family optimiser product expansion, save/spend logic, and broader planning behaviour built on top of the already-governed lower-layer income surfaces.

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

## Phase 4 — Full stat-resolution migration to Query Engine

### Purpose
Make Query Engine the practical and declared owner of canonical stat-resolution truth, fully vacate `engine/stat_resolution_core.py` as a canonical logic owner, and leave `engine/stat_engine.py` only as thin compatibility entrypoint if still needed.

### Target end-state
By end of Phase 4:
- canonical stat-resolution scope is KB aligned
- canonical stat-resolution scope resolves through Query Engine-owned paths
- `engine/stat_engine.py` may remain only as thin compatibility entrypoint
- `engine/stat_resolution_core.py` owns no canonical stat logic
- retained legacy files, if any, exist only as non-canonical merge/reference aids for reconciling code built from older baselines
- new stat surfaces coming into scope must plug into KB + QE, not legacy paths

### Phase-wide rules
- New canonical stat logic may not be added to `engine/stat_engine.py` or `engine/stat_resolution_core.py`.
- If either legacy file is retained after Phase 4, its role must be explicitly non-canonical and reference-only.
- Presence of a legacy file does not imply permission to route new stat truth through it.
- Phase 4 scope denominator must be frozen before code migration begins.
- Completion is measured by ownership and routing truth, not by file deletion aesthetics.

### Canonical denominator freeze
Phase 4 must freeze the denominator before migration code begins. That denominator governs exactly what counts as:
- canonical stat-resolution families in scope
- canonical stat groups in scope
- allowed retained legacy merge/reference residue
- parity-covered migrated scope
- benchmark-covered migrated workloads

The frozen denominator must explicitly classify every surface or group into one of these categories only:
1. `family_scoped_canonical_resolution`
2. `non_family_canonical_stat_resolution`
3. `compatibility_only_surface`
4. `legacy_merge_reference_residue`
5. `out_of_phase4_scope`

No Phase 4 tranche may:
- add a new in-scope category
- move a surface between categories
- expand canonical scope silently
- claim migration completion against a changed denominator

unless the three control files are deliberately revised first.

PH4-A must freeze, in one explicit ledger, all of the following before code migration begins:
- the exact family universe counted as migrated/not-migrated
- the exact canonical stat groups counted as migrated/not-migrated
- the exact residual buckets allowed after Phase 4, if any
- the exact parity denominator
- the exact benchmark denominator

No later tranche may silently expand or shrink those denominators. If the denominator must change, stop and update all three control files before continuing.

### Tranches
- PH4-A — Canonical migration ledger and denominator freeze
- PH4-B — Declared family cutover to Query Engine
- PH4-C — Canonical stat group migration by dependency order
- PH4-D — Parity matrix and benchmark closure for migrated scope
- PH4-E — Control-truth cutover and legacy demotion
- PH4-F — Post-cutover hardening and closeout

### PH4-A — Canonical migration ledger and denominator freeze
Goal:
- freeze exactly what counts as canonical stat-resolution scope, residual scope, migrated scope, and benchmark/parity denominator

Scope in:
- full migration ledger
- current-owner vs target-owner mapping
- residual categories
- explicit allowed legacy merge-reference status

Scope out:
- code migration
- formula changes
- parity execution
- benchmark execution

Owner surfaces:
- `AI_EXECUTION_PLAN.md`
- `ACTIVE_TRANCHE.md`
- `BURNDOWN.yaml`
- `engine/stat_resolution_core.py`
- `engine/stat_engine.py`
- `engine/stat_query_kernel.py`
- `kb/global-rules/contracts/stat-query-scenario-families.yaml`
- `kb/global-rules/contracts/stat-query-initial-surface-set.yaml`
- `kb/global-rules/contracts/stat-query-consumer-bundles.yaml`

Forbidden surfaces:
- `optimizer/`
- simulator product modules
- evaluator implementation modules
- `run_stats.py` beyond inventory support if strictly necessary

Required outputs:
- canonical migration ledger
- denominator freeze note
- residual bucket statement
- explicit post-Phase-4 legacy-file rule

Required verification:
- every in-scope canonical stat family/group is named
- every row names current owner and target owner
- every row names whether any post-phase residue is allowed
- no code migration begins before denominator is frozen

Stop conditions:
- stop if a canonical stat group cannot name target QE owner
- stop if a surface cannot be assigned to either canonical scope or explicit residual bucket
- stop if a denominator change is discovered after implementation begins without updating all three control files first

### PH4-B — Declared family cutover to Query Engine
Goal:
- move all already-declared scenario families to live Query Engine-owned resolution

Scope in:
- live cutover for all declared families
- query routing/materializer/kernel work needed for those families
- family-level regression tests

Scope out:
- undeclared family expansion
- long-tail non-family stat migration
- optimiser/evaluator feature work

Owner surfaces:
- `engine/stat_engine.py`
- `engine/stat_query_kernel.py`
- `engine/family_baseline_materializer.py`
- `engine/query_routing.py`
- `engine/query_state_mode_policy.py`
- `engine/query_perk_compiler.py`
- `compilers/stat_input_compiler.py`
- `kb/global-rules/contracts/stat-query-scenario-families.yaml`
- `kb/global-rules/contracts/stat-query-initial-surface-set.yaml`
- `kb/global-rules/contracts/stat-query-consumer-bundles.yaml`
- `tests/test_resolve_stats_delegation.py`

Forbidden surfaces:
- `optimizer/`
- simulator product modules
- evaluator implementation modules
- new generic helper sink files

Required outputs:
- live delegation for all declared families
- updated family routing logic
- family coverage tests
- updated migration KPI counts

Required verification:
- all declared families are live-routable through QE path
- undeclared surfaces are not swept into family routing silently
- any blocked family residue is explicit and bounded

Stop conditions:
- stop if family coverage would require changing undeclared consumer semantics
- stop if a family cannot be routed without inventing new surface classes
- stop if code changes would touch files outside listed owner surfaces without control-file update

### PH4-C — Canonical stat group migration by dependency order
Goal:
- move remaining canonical stat-resolution logic out of legacy ownership and into QE-owned paths in strict dependency order

Scope in:
- migration of canonical stat groups named in PH4-A ledger only
- duplicate-logic removal as groups move
- targeted tests and parity support per group

Scope out:
- simulator product work
- optimiser feature work
- archive cleanup
- undocumented long-tail helper beautification outside frozen denominator

Owner surfaces:
- `engine/stat_resolution_core.py`
- `engine/stat_engine.py`
- `engine/stat_query_kernel.py`
- `engine/family_baseline_materializer.py`
- `engine/dependency_registry.py`
- `kb/global-rules/contracts/stat-query-initial-surface-set.yaml`
- `kb/global-rules/contracts/stat-query-consumer-bundles.yaml`
- `tests/`

Forbidden surfaces:
- broad `run_stats.py` refactor
- `optimizer/`
- `advisors/`
- new architecture layers

Required outputs:
- migrated canonical stat groups from frozen denominator only
- explicit residual list after each migrated group
- parity fixtures/tests per group
- updated ownership statements

Required verification:
- each migrated group has explicit before/after ownership
- no migrated group still relies on legacy formula truth for final value
- any blocked surface is added to explicit residual ledger
- no duplicate logic remains for migrated surfaces

Stop conditions:
- stop if a lower-dependency group is incomplete but a higher-dependency group is about to start
- stop if a group cannot be migrated without changing mechanics not yet governed in KB
- stop if a migrated surface still needs legacy final-value truth to compute output
- stop if a change would migrate a surface not frozen in PH4-A denominator

### PH4-D — Parity matrix and benchmark closure for migrated scope
Goal:
- prove migrated QE surfaces match acceptable reference truth closely enough to cut over ownership

Scope in:
- family parity matrix
- canonical stat group parity matrix
- benchmark capture for migrated workloads
- explicit cutover readiness decision

Scope out:
- new migration work beyond bugfixes triggered by parity failure
- simulator/optimiser feature work

Owner surfaces:
- `tests/`
- `out/` when rebuilt governed artifacts are needed as evidence
- `BURNDOWN.yaml`
- `ACTIVE_TRANCHE.md`

Forbidden surfaces:
- broad new code paths
- new families
- new layer creation

Required outputs:
- parity matrix by family/group/surface
- benchmark evidence for migrated workloads
- explicit pass/fail/open status
- cutover readiness note

Required verification:
- every migrated family/group has visible parity status
- benchmark evidence exists for workloads that matter for cutover
- failures are explicit and bounded

Stop conditions:
- stop if parity denominator is unclear
- stop if benchmark workload is not tied to actually migrated path
- stop if any claimed pass cannot be defended with concrete evidence

### PH4-E — Control-truth cutover and legacy demotion
Goal:
- make QE the declared canonical owner in control truth and narrow legacy code to non-canonical residue only if any remains

Scope in:
- control-truth cutover
- narrowed compatibility path
- legacy demotion/quarantine statement
- canonical owner statement updates

Scope out:
- new feature work
- unrelated cleanup
- broad `run_stats.py` decomposition

Owner surfaces:
- `AI_EXECUTION_PLAN.md`
- `BURNDOWN.yaml`
- `ACTIVE_TRANCHE.md`
- `engine/stat_engine.py`
- `engine/stat_resolution_core.py`
- `ARCHITECTURE.md`
- `README.md`
- affected tests/docs

Forbidden surfaces:
- simulator product modules
- optimiser feature work
- advisor work
- new compatibility shims unless explicitly named residuals require them

Required outputs:
- updated canonical ownership wording
- narrowed compatibility path
- legacy demotion/quarantine statement
- residual ledger of anything not fully retired

Required verification:
- control truth no longer names `stat_resolution_core.py` as canonical owner
- `stat_engine.py` is clearly thin compatibility only
- any remaining residue is named, bounded, and temporary
- dual ownership language is removed from major docs

Stop conditions:
- stop if cutover would hide unresolved residuals
- stop if docs would claim full retirement while code still depends materially on legacy final-value truth
- stop if a compatibility shim is added without explicit residual ownership note

### PH4-F — Post-cutover hardening and closeout
Goal:
- close the phase cleanly after cutover, prove no control drift remains, and hand stable ownership to later phases

Scope in:
- post-cutover smoke/proof pass
- final KPI values
- stale-reference cleanup
- phase closeout and promotion readiness

Scope out:
- new migration work
- new feature work
- opportunistic cleanup beyond directly stale references

Owner surfaces:
- `AI_EXECUTION_PLAN.md`
- `BURNDOWN.yaml`
- `ACTIVE_TRANCHE.md`
- `README.md`
- `ARCHITECTURE.md`
- directly stale test/docs references

Forbidden surfaces:
- new architectural changes
- product features
- new files unless required by control truth and explicitly justified

Required outputs:
- phase closeout note
- final migration KPI values
- stale-reference cleanup
- next-phase promotion note

Required verification:
- all PH4 exit-gate conditions are explicitly satisfied or blocked with named exception
- stale references to legacy canonical ownership are removed
- next phase can begin without ownership ambiguity

Stop conditions:
- stop if phase closeout would require claiming stronger cutover than evidence supports
- stop if any major doc still implies dual ownership
- stop if KPI ledger has unresolved contradictions

### Phase 4 exit gate
- canonical stat-resolution scope is KB aligned
- canonical stat-resolution scope resolves through QE-owned paths
- `engine/stat_engine.py` is thin compatibility only if retained
- `engine/stat_resolution_core.py` owns no canonical stat logic
- any retained legacy file exists only as non-canonical merge/reference aid
- parity exists for migrated scope
- benchmark evidence exists for migrated workloads
- control files, tests, and docs no longer imply dual ownership

---

## Phase 5 — Verification, evaluator foundation, and test acceleration

### Purpose
Make verification first-class, establish evaluator substrate, and create explicit test-lane/benchmark policy on top of a stable stat-resolution owner model.

### Tranches
- PH5-A — Surface verification registry
- PH5-B — Evaluator contract framework
- PH5-C — Max-wave evaluator reference corpus
- PH5-D — Max-wave evaluator implementation or hardening
- PH5-E — Evaluator verification matrix
- PH5-F — Test inventory and timing profile
- PH5-G — Test lane redesign and CI policy alignment

### Exit gate
- governed verification registries exist
- evaluator inputs/outputs/assumptions are explicit
- reference corpus exists for evaluator verification
- evaluator verification status is visible by case family
- test lanes are defined and CI policy matches them

---

## Phase 6 — `run_stats.py` decomposition and thin orchestration

### Purpose
Shrink `run_stats.py` after ownership and proof systems are stable.

### Tranches
- PH6-A — `run_stats.py` decomposition map
- PH6-B — reporting extraction
- PH6-C — verification/comparison extraction cleanup
- PH6-D — output emission and orchestration cleanup

### Exit gate
- every major remaining concern in `run_stats.py` has a target owner
- extracted modules have clear ownership
- `run_stats.py` is primarily orchestration
- outputs remain stable and validated

---

## Phase 7 — Simulator product surfaces

### Purpose
Build simulator product surfaces on top of QE-owned stat truth and evaluator substrate.

### Tranches
- PH7-A — survivability simulator
- PH7-B — damage-aware run-limit simulator
- PH7-C — setup comparison simulator
- PH7-D — richer run-outcome explanation

### Exit gate
- simulator interfaces are consistent
- failure-mode classification is explicit
- simulator surfaces use governed lower-layer truth
- maturity and trust labels are explicit

---

## Phase 8 — Optimiser product surfaces

### Purpose
Build optimiser families on top of QE-owned objective states and verified evaluators.

### Tranches
- PH8-A — loadout optimiser
- PH8-B — progression optimiser core
- PH8-C — resource-family optimiser expansion
- PH8-D — save-vs-spend and branching logic
- PH8-E — archive helper re-homing where justified

### Exit gate
- optimisers consume stable lower-layer surfaces
- objective families are explicit
- recommendation confidence and trust logic are visible
- save-vs-spend branching is governed

---

## Phase 9 — Advisor surfaces and external interfaces

### Purpose
Build user-facing planning and strategy surfaces after lower layers are trustworthy.

### Tranches
- PH9-A — progression-planning advisor
- PH9-B — build-transition advisor
- PH9-C — external query and API schema
- PH9-D — advisor explanation and trust-label packaging

### Exit gate
- advisor outputs consume governed lower layers
- strategy explanations are traceable
- external interfaces expose stable schema
- trust labels remain explicit

---

## Phase 10 — Archive retirement and cleanup closure

### Purpose
Retire superseded root artifacts only after their truth has been absorbed or explicitly rejected.

### Tranches
- PH10-A — remaining archive artifact retirement
- PH10-B — final pointer cleanup across docs and repo surfaces

### Exit gate
- no active work depends on retired root artifacts
- all retained truths are represented in canonical in-repo sources
- repo docs point to current truth, not legacy bundles

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
