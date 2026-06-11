# TowerSim Bible v49

Status: Living authoritative working document  
Version: v49  
Date: 2026-04-09  
Owner: Harry  
Primary execution agents: ChatGPT, Codex, other AI tooling  
Primary human operator: Harry  
Repo baseline covered here: current live local repo, truth-synced from the original `tower-sim-src.zip` baseline through the active v49 worktree  
Supersedes for active execution scope:
- `TowerSim_bible_v47.md`
- `TowerSim_bible_v48.md`
- any separately preserved evaluator-kernel or run-executor companion spec
- stale active-tranche/governance wording in the uploaded repo where it conflicts with this scope reset

---

## 0. How to use this document

This is not a history file and not a brainstorm.

It is the single active build constitution for the current TowerSim handoff state.

It exists so a coding agent can answer, without improvising:

1. What TowerSim is currently trying to become.
2. What is true in the current live repo baseline.
3. What counts as in scope right now.
4. What architecture and ownership rules must not be violated.
5. What must happen next, in what order, and what counts as done.

### Evidence labels used in this document

- **Verified-live**: directly confirmed from the uploaded v47/v48 bibles, current live repo files, current committed/generated artifacts, or current tests inspected in this pass.
- **Verified-imported**: preserved from earlier audited bible content and retained because it still expresses a useful contract, but not freshly re-proven from live code in this pass.
- **Decision**: active execution choice or governance rule locked for the current scope.
- **Inference**: reasoned conclusion consistent with inspected evidence, but not yet proven by implementation or benchmark rerun.

Rule:
- live repo evidence outranks stale repo governance text
- this bible outranks earlier bibles
- this bible outranks separate companion specs
- if code and docs disagree, prefer code/tests/artifacts and update docs later
- if scope is ambiguous, stop rather than guess

### Core rules

1. In an AI-first repo, ambiguity is a defect.
2. One concept should have one obvious owner.
3. Streamlit is the primary operational surface, but not a second engine.
4. QE remains the canonical owner of stat truth.
5. Simulators remain the canonical owner of run-state evolution and max-wave logic.
6. Publication and Streamlit may shape and display truth, but must not invent it.
7. No second live authority may sit beside this bible for the current scope.

### 0.1 Scope lock for v49

**Decision**

The active scope for this version is:

- make every canonical, user-relevant stat visible in Streamlit
- make those visible stats KB/QE aligned, provenance-bearing, and contract-governed
- deliver the max-waves simulator through the Streamlit product surface
- include the performance contract required for interactive use
- include bloat/residue/duplicate-authority removal where it improves truth, speed, or navigability
- explicitly exclude evaluator and optimiser delivery from the current completion target

This is broader than “finish Workshop” and narrower than “finish the whole platform”.

### 0.2 Why v49 exists

**Verified-live + Decision**

Bible v48 was a strong staged continuation document, but it was still anchored to the older `tower-sim-src v11.zip` baseline and a visible-stat-first program that deferred simulator delivery and preserved a separate future evaluator-kernel design asset.

The live repo plus the current thread instructions materially change that operating frame:

- the live repo is newer than the v48 baseline
- repo governance files contain active v49 Streamlit-first simulator/stat program records, while historical maintenance-stabilization notes remain preserved as context
- the repo already moved beyond at least part of the old Workshop completeness gap, specifically `Interest / Wave` and `Wall Rebuild`
- the user has now locked the active product target as Streamlit-first, with every canonical stat visible and the max-waves simulator delivered, and has explicitly asked for the old kernel document to be consolidated into the bible rather than retained as a second authority

Therefore v49 is a scope-reset and authority-collapse version, not a cosmetic renumbering.

### 0.3 Source corpus reconciled for v49

**Verified-live**

This document has been built against:

- `TowerSim_bible_v47.md`
- `TowerSim_bible_v48.md`
- latest live local repo snapshot
- current root governance files inspected from that repo:
  - `ACTIVE_TRANCHE.md`
  - `BURNDOWN.yaml`
  - `ARCHITECTURE.md`
  - `README.md`
  - `AGENTS.md`
- current implementation files inspected directly:
  - `app/pipeline.py`
  - `app/streamlit_inspector.py`
  - `qe/run_plan.py`
  - `simulators/evaluator_kernel.py`
  - `simulators/timing.py`
  - `simulators/scenario.py`
  - `tests/app/test_stats_dashboard_contract.py`
  - `tests/app/test_pipeline_functional.py`
  - `tests/simulators/test_evaluator_kernel.py`
  - `tests/simulators/test_core_smoke.py`
  - `tests/shared/test_import_boundaries.py`
- current committed artifacts inspected directly:
  - `out/run_stats_query_rows_start_of_run.json`
  - `out/run_stats_query_rows_max_progression.json`

### 0.4 What changed from v48

**Decision**

v49 makes these material changes:

1. Replaces the prior T1/T2/T3 rollout program as the active execution frame.
2. Replaces the older “visible-stat-first then later simulator/evaluator summaries” staging with a single current program:
   - canonical stat visibility in Streamlit
   - max-wave simulator delivery through Streamlit
   - performance and cleanup required to make that usable
3. Absorbs the useful parts of the old future kernel/evaluator spec into this document.
4. Removes separate live authority for any companion kernel spec.
5. Preserves the visible-stat contract, performance contract, migration discipline, and deletion-gated cutover rules from v48.
6. Explicitly records that the latest repo appears to have closed part of the old Workshop gap, so Codex must not reopen already-fixed issues.
7. Truth-syncs the simulator authority from the removed `simulators/run_executor.py` row-engine to the current Boss Waves replacement path centered on `qe.run_plan`, `simulators.evaluator_kernel`, `simulators.timing`, `simulators.scenario`, and sanctioned app orchestration.

---

## 1. Executive product definition

### 1.1 What TowerSim is for this stage

**Decision**

For the current stage, TowerSim is:

> a Streamlit-first, single-operator, AI-assisted reasoning instrument for The Tower that exposes canonical stat truth, explains where that truth came from, and projects survivability to max wave through a simulator backend.

It is not currently trying to be:
- a multi-user platform
- a polished general-purpose API product
- a completed evaluator/optimiser platform
- a CI/precompute-heavy service

### 1.2 What “complete” means for this stage

**Decision**

The current program is complete only when all of the following are true:

1. Every canonical, user-relevant stat required for real operator use has a visible home in Streamlit.
2. Those visible stats resolve from the sanctioned authority chain:
   `input -> kb -> qe -> publication/app -> Streamlit`.
3. Missingness, provenance, reconciliation status, and special rules are explicit rather than implied.
4. The max-waves simulator is usable through Streamlit and is backed by sanctioned simulator ownership rather than UI-local or evaluator-local shortcuts.
5. The stat and simulator surfaces are fast enough for interactive use according to the performance contract in this bible.
6. Duplicate authority, stale residue, and hot-path drag that would mislead AI or slow the product have been removed or explicitly quarantined.
7. Governance text and active instructions materially match the actual implementation scope.

### 1.3 What is out of scope

**Decision**

Out of scope for v49 completion:

- evaluator product delivery
- optimiser product delivery
- broad archival cleanup unrelated to truth/speed/authority
- CI-driven default precompute as a dependency for basic success
- speculative new subsystems
- preserving old hot paths “just in case” after parity is proven

---

## 2. Real usage model and why it changes the architecture

### 2.1 Actual usage model

**Verified-live + Decision**

Current practical reality remains:

- Harry is the only real human operator.
- AI is the main implementation agent.
- AI is also the main reader of docs, file structure, tests, and control surfaces.
- Streamlit is not just a debug UI. It is the intended operational front-end.
- The repo is therefore best treated as a single-operator reasoning instrument, not a normal collaborative software project.

### 2.2 Consequences of that usage model

**Decision**

The repo should optimize for:

- one obvious truth source per concept
- one obvious active path per operation
- visible and inspectable truth
- reusable, fast interaction through Streamlit
- compact but authoritative docs
- deletion of stale plausible-looking residue
- fail-closed behavior when authority is ambiguous

The repo should not optimize for:

- doc sprawl
- parallel “temporary” paths that look equally real
- framework theatre
- preserving historical alternatives inside the active surface

### 2.3 Streamlit-first does not mean Streamlit-owned logic

**Decision**

The correct product stance is:

- Streamlit is the only operational UI
- Streamlit is the main observability/debugging surface
- Streamlit must not become a second calculation engine

Therefore:

- Inputs own imported/manual state
- KB owns formulas/tables/contracts
- QE owns canonical stat truth
- Simulators own run-state evolution and max-wave logic
- publication/app own payload shaping and orchestration only
- Streamlit renders, inspects, filters, and controls only

---

## 3. Authority order and repo model

### 3.1 Current active authority order

**Decision**

For the current scope, authority order is:

1. this bible
2. live repo code, tests, and committed artifacts in the current local repo
3. repo root governance files, only where they do not conflict with this bible
4. earlier bibles, only for preserved context
5. any older companion spec, only insofar as its useful clauses have been explicitly absorbed here

### 3.1A Repo-local AGENTS and skills status

**Decision**

Repo-local `AGENTS.md`, Codex skills, and startup prompts are workflow machinery only.

They may:
- force the correct preflight
- enforce phase discipline
- enforce freeze / certification checks
- reduce drift and token waste

They may not:
- replace this bible as product-and-scope authority
- replace live repo code/tests/artifacts as implementation-reality authority
- introduce a second design authority
- widen scope beyond v49

If a repo-local instruction, skill, or prompt conflicts with this bible, the bible wins. If it conflicts with live implementation reality, treat it as stale workflow machinery and update it rather than following it blindly.

### 3.2 Layer ownership rules

**Decision**

Ownership remains:

- `input/` owns imports, parsing, manual inputs, runtime-state assembly
- `kb/` owns mechanic truth, tables, ledgers, contracts
- `qe/` owns stat/query contracts, routing, compilation, canonical resolution, visible query rows
- `simulators/` owns timing, progression, perk timeline application, run-state evolution, max-wave logic
- `evaluators/` is downstream and out of current product scope
- `advisors/` is downstream and out of the active completion target
- `app/` owns sanctioned orchestration and payload shaping only
- `app/streamlit_inspector.py` owns UI presentation only
- `tests/` own regression protection and contract enforcement

### 3.2A Simulator timing and geometry ownership

**Verified-live + Decision**

Timing is an active simulator owner surface.

`simulators/timing.py` owns time-based mechanics and reusable timing calculations, including:

- wave duration and Wave Accelerator timing
- cooldown/duration uptime fractions
- boss contact time and boss hit interval calculations
- Energy Net hold and mastery damage-window timing
- timed damage-reduction source construction and lane composition
- time-limited damage windows used by Boss Waves diagnostics and kernel consumers

`app/` may pass inputs into these helpers and publish their outputs, but must not own duplicate timing math.

Geometry is a separate simulator concern, but it is not yet a formal direct file in the live architecture.

Current live contracts already anticipate geometry state via `geometry_dirty`, `geometry_recompute_count`, and `geometry_context`. A future geometry tranche may add `simulators/geometry.py`, but doing so must update:

- `ARCHITECTURE.md`
- `REPO_INDEX.yaml`
- matching import/inventory boundary tests
- call sites that currently hold spatial calculations in the timing/Boss Waves path

Expected split:

- timing owns **when** something is active, how long it lasts, and how timing windows overlap
- geometry owns **where** things are, range/radius normalization, area/path overlap, and spatial hit probability

Until the geometry tranche is explicitly implemented, no code may invent a second geometry authority or add a new simulator file without the architecture inventory update.

### 3.3 Current repo truth snapshot

**Verified-live**

The latest extracted repo currently contains, at top level:

- root governance/docs: `ACTIVE_TRANCHE.md`, `AGENTS.md`, `ARCHITECTURE.md`, `BURNDOWN.yaml`, `README.md`, `REPO_INDEX.yaml`, `RTK.md`
- active code surfaces: `input/`, `kb/`, `qe/`, `simulators/`, `evaluators/`, `advisors/`, `app/`, `tests/`, `out/`

Current truth that matters most:

- root governance contains active v49 Streamlit-first canonical stat and simulator program records, while some historical entries still preserve earlier cutover notes and stale maintenance wording
- current Streamlit tab order is:
  - Input
  - QE
  - Stats
  - Boss Waves
  - Pipeline
  - Checks
- current Streamlit already has an interactive Boss Waves surface
- `app/pipeline.py` wires `build_boss_wave_payload(...)`
- `build_boss_wave_payload(...)` is the sanctioned product orchestration surface for Boss Waves payload assembly
- Boss Waves replacement product behavior is centered on:
  - `qe.run_plan` for compiled RunPlan/common-trajectory primitives and staged contributor bundles
  - `simulators.evaluator_kernel.build_scenario_overlay_table(...)` for Table 2 scenario overlays, boss TTK/TTD, lane evaluation, and selected survival semantics
  - `simulators.timing` for boss contact time, hit interval, timed DR source/lane semantics, Energy Net timing, Flame Bot timing-weighted hit chance, and time-limited damage windows
  - `simulators.scenario`, `simulators.progression`, `simulators.perk_timeline_generator`, `simulators.perk_timeline_state`, and `simulators.wave_progression_policy` for scenario, progression, and perk/run-state behavior
- `simulators/run_executor.py` has been removed from the live repo and must not be recreated as a compatibility shim
- replacement-era simulator verification is through `tests/simulators/test_evaluator_kernel.py`, `tests/simulators/test_core_smoke.py`, `tests/simulators/test_boss_waves_parity_shadow.py`, and product-facing app tests
- current committed query-row artifacts include:
  - `state::economy.interest_per_wave_pct`
  - `state::wall.rebuild_seconds`
  - `state::tower.thorns_damage_pct`

### 3.4 Current repo mismatch that v49 explicitly overrides

**Verified-live + Decision**

Earlier root governance lagged behind the v49 product program. The live governance files have since been partly truth-synced, but historical completion notes still appear in them.

Rule:
- Codex must treat this bible as the active product scope.
- root governance files are execution-control companions only where they agree with this bible and live implementation reality.
- stale historical notes must not be used to revive removed code paths or older completion claims.
- v49 is the scope reset and active build constitution.

---

## 4. Canonical visible-stat and observability contract

### 4.1 Purpose

**Decision**

This section promotes the former v48 appendix contract into core active authority.

Its purpose is to ensure that “every stat visible in Streamlit” means:
- complete
- consistent
- explainable
- comparable
- not bespoke per domain

### 4.2 Definition of “every stat”

**Decision**

For the current stage:

> “Every stat” means every canonical, user-relevant, operator-meaningful stat surface needed to understand the account, loadout, runtime state, and simulator behavior through Streamlit.

It does **not** mean:
- every transient local variable
- every internal scratch accumulator
- every helper-only intermediate
- every artifact-only bookkeeping field

A surface must be visible if at least one of these is true:
1. the operator needs to inspect it to understand current build strength or weakness
2. it is a direct gameplay stat or policy driver
3. it materially affects simulator outcomes
4. it is needed to explain provenance, reconciliation, or missingness for another visible stat

### 4.3 Required visible-domain classes

**Decision**

The current visibility program must cover, at minimum, these classes:

1. **Input-owned source domains**
   - workshop
   - enhancements
   - labs
   - cards
   - modules
   - relics
   - ultimate weapons
   - bots
   - guardians
   - vault and other progression drivers where they affect visible canonical stats
   - manual/runtime policy inputs where they materially change resolution or simulation

2. **QE-owned resolved stat domains**
   - offense
   - defense
   - utility/economy
   - package/recovery
   - wall and survivability surfaces
   - derived composites
   - timing-relevant resolved surfaces
   - simulator-required resolved surfaces
   - other canonical stat families that materially affect visible use

3. **Simulator-owned visible summary domains**
   - boss-wave table
   - max-wave summary
   - simulator diagnostics needed to explain the result
   - scenario/runtime inputs actually used by the run

### 4.4 Common row metadata contract

**Decision**

Every visible stat row must carry enough metadata to answer:

- what is this
- who owns it
- where did it come from
- is it resolved, missing, partial, or special-case
- whether it reconciles and by what rule
- whether its current values are comparable across state modes/presets

Minimum row-level requirements:

- stable display name
- canonical surface id or explicit declaration that no query-row is required
- owner layer
- value type / family
- start-of-run and max-progression values where applicable
- row status
- reconciliation status where applicable
- contributor list or explicit reason not shown
- notes for special rules or declared omissions

### 4.5 Canonical row-status semantics

**Decision**

Allowed status semantics for visible rows:

- `resolved`
- `partially_resolved`
- `mapped_not_resolved`
- `missing`
- `non_recon`
- `not_applicable`
- explicit declared special-case status only if it is named and tested

Rules:

- no silent `None` semantics for operator-visible meaning
- no green row by undeclared special handling
- if a row is missing, the reason must be explicit
- if a row is non-reconciling by design, that must be explicit

### 4.6 Reconciliation rules

**Decision**

Reconciliation must be:

- numeric/effect-first, not display-first
- family-aware
- field-aware
- special-case-explicit

Do not judge correctness only from rendered tokens like `x 1` or `+ 0`.

Visible special rules must be declared in the row contract or domain contract, not silently hard-coded in UI logic.

### 4.7 Compare semantics

**Decision**

A visible surface must not pretend comparability if provenance or schema makes that false.

Compareability requires:

- same canonical surface meaning
- same value family
- compatible provenance or explicit adaptation
- clear distinction between source values and resolved values
- no hidden reinterpretation between state modes

### 4.8 Ownership rules for visible domains

**Decision**

For any visible domain rollout:

- QE owns canonical query rows for canonical stat truth
- publication/app may group, rename for display, add notes, and render explicit missingness
- Streamlit may only consume those payloads and provide UI controls
- tests must verify the contract
- helper or line-verification data must not silently backfill missing canonical rows

### 4.9 Workshop remains the reference implementation

**Decision**

Workshop remains the reference domain for:

- row semantics
- contributor semantics
- reconciliation semantics
- missingness semantics
- anti-backfill rules

But v49 explicitly corrects the stale v48 assumption that Workshop still had the same three open completeness gaps.

### 4.10 Repo delta note: old Workshop gap is partly stale

**Verified-live**

The latest repo indicates that at least part of the old v48 Workshop completeness list has moved on:

- current committed query-row artifacts include `state::economy.interest_per_wave_pct`
- current committed query-row artifacts include `state::wall.rebuild_seconds`
- current tests include explicit “green when QE rows exist” cases for those rows
- current naming for thorns in committed QE surfaces is `state::tower.thorns_damage_pct`, not the older `state::wall.thorns_damage_pct`

Therefore:

- Codex must not reopen `Interest / Wave` or `Wall Rebuild` as if they are still absent from QE query rows
- Codex must verify current `Wall Thorns` naming and visibility against the live repo rather than blindly following the older v48 text
- v48’s old Workshop gap list is preserved as history, not as current truth

---

## 5. Max-waves simulator contract

### 5.1 Purpose

**Decision**

This section absorbs the useful simulator/kernel ideas into the active bible so there is no separate live kernel authority.

The simulator program for the current scope is:

> deliver a trustworthy max-waves result through Streamlit using sanctioned simulator ownership, sanctioned QE inputs, and explicit diagnostics.

### 5.2 Active implementation authority for the current stage

**Verified-live + Decision**

The active simulator implementation authority for the current stage is the live replacement path centered on:

- sanctioned app wiring in `app/pipeline.py`, especially `build_boss_wave_payload(...)`
- `qe/run_plan.py` for compiled RunPlan/common-trajectory inputs and staged contributor bundles
- `simulators/evaluator_kernel.py` for Boss Waves Table 2 overlay rows, boss TTK/TTD, lane evaluation, and selected survivability semantics
- `simulators/timing.py` for timing/wave projection and reusable timing mechanics
- `simulators/scenario.py` for scenario projection and tier battle-condition surfaces
- `simulators/progression.py` and `simulators/wave_progression_policy.py` for progression and skip mechanics
- `simulators/perk_timeline_generator.py` and `simulators/perk_timeline_state.py` for perk timeline generation and perk state application

Important implication:
- there is no separate active kernel spec
- the useful clauses from the old companion spec are consolidated here
- `simulators/run_executor.py` has been removed and must not be recreated as a compatibility shim
- future simulator work must improve or replace the active path only by parity-proven cutover and deletion, not by leaving dual primary authorities

### 5.3 Current live simulator shape

**Verified-live**

The current repo already exposes:

- a Streamlit “Boss Waves” surface that currently routes through `build_boss_wave_payload(...)`
- replacement-backed operator rows, summary rows, diagnostics, and optional all-tier milestone matrix output through sanctioned app orchestration
- `qe.run_plan` compiled common-trajectory and survivability contributor inputs
- `simulators.evaluator_kernel.build_scenario_overlay_table(...)` as the replacement Boss Waves kernel
- `simulators.timing` helpers for contact time, hit interval, timed DR, Flame Bot timing/hit chance, Energy Net timing, and wave duration
- replacement-era tests that cover evaluator-kernel rows, Boss Waves product payloads, timing engine helpers, import boundaries, and parity/certification behavior

### 5.4 What the max-waves simulator must mean

**Decision**

For the current stage, the simulator must answer:

1. Under a selected preset, state mode, tier, and runtime scenario, how far does the build survive?
2. What is the max surviving wave?
3. What boss-wave path and diagnostics explain that outcome?
4. Which canonical resolved surfaces materially drove the result?

It does not need to become a general evaluator kernel in this stage.

### 5.5 Trust requirements for max-wave credibility

**Decision**

Stat correctness alone is not enough.

The current max-wave simulator is only trustworthy if it uses and/or truthfully models:

- timing behavior
- perk policy / perk timeline
- dynamic run-state transitions
- wave progression and skip mechanics
- boss-wave stepping discipline
- boss TTK logic
- boss damage intake logic
- surviving pool semantics using the sanctioned current survivability contract
- explicit runtime scenario inputs used by the run

### 5.6 Streamlit product requirement

**Decision**

The simulator is not complete for this stage until it is visible and usable through Streamlit.

Minimum Streamlit simulator product requirements:

- selected preset
- selected tier
- scenario/runtime controls that actually affect the run
- max-wave / max-surviving-wave summary
- boss-wave table or equivalent stepped diagnostic view
- execution diagnostics
- clear indication of checkpoint/boss-wave stepping mode
- downloadable or inspectable row output for debug/review
- no hidden alternate simulator path outside the visible operational surface

### 5.7 Simulator input contract

**Decision**

Simulator code must consume sanctioned state and resolved surfaces, not ad hoc UI blobs.

Required current input model:

- account/runtime state built by the input layer
- sanctioned QE-resolved or snapshot-resolved surfaces
- explicit runtime scenario inputs
- explicit preset / state-mode / tier selection
- explicit stepping configuration

Unsupported or malformed caller intent must be rejected before timed execution.

### 5.8 Preserved kernel principles now absorbed into active authority

**Decision**

The following old kernel ideas are preserved and now live here:

1. **Compile-before-run discipline**
   - normalize and validate caller intent before timed execution

2. **Stable schema discipline**
   - simulator result objects and summary payloads need stable identity and versioned semantics once returned

3. **No benchmark theatre**
   - benchmark repetitions must execute the real sanctioned path
   - no benchmark-only hidden fast path
   - no “success” that comes from returning precomputed summary rows while pretending it measured computation

4. **Cache/invalidation honesty**
   - if cache is used, disclosure must be explicit
   - warm-path claims must not be smuggled into cold-path claims

5. **Cutover/removal discipline**
   - if a new simulator path is introduced later, it must follow:
     - parallel build
     - shadow validate
     - cut over
     - remove/demote legacy path

6. **Hot-path data-layout discipline**
   - avoid dict-per-row or string-heavy object-graph hot loops where a flatter structure is possible
   - this is a direction for implementation shape, not permission for a giant rewrite

### 5.9 Preserved formula-structure guidance worth keeping

**Verified-imported + Decision**

The following clauses are worth preserving as simulator-shape guidance because they constrain future drift:

- boss TTK should remain event-structured rather than degraded into an unjustified additive-DPS shortcut
- damage-intake logic should stay explicitly lane/model based rather than widened implicitly
- package timing or other optional mechanics should not silently widen the minimal survivability contract without explicit approval
- death-cause taxonomy should remain bounded rather than sprawling through the hot path

These clauses are now active guardrails rather than separate-spec residue.

### 5.10 Current simulator completion definition

**Decision**

The max-waves simulator counts as complete for this scope only when all are true:

1. Streamlit can run it in the sanctioned operational surface.
2. The visible max-wave result is backed by the sanctioned simulator path.
3. The boss-wave table and summary agree with the result.
4. Required simulator inputs are explicit and visible.
5. Core run diagnostics are visible.
6. Current survivability semantics are explicit and not silently widened.
7. Current simulator tests pass.
8. Performance and benchmark evidence for the sanctioned path are recorded honestly.
9. No second live kernel authority remains.

---

## 6. Performance contract

### 6.1 Performance targets preserved from v48

**Decision**

Current targets retained from v48:

- loadout delta: target `< 50 ms`
- full stats refresh: target `< 100 ms`
- preset switch: directionally close to instant once the architecture is solid and warm, but current stage must measure it honestly rather than fake it with precompute theatre

### 6.2 Performance principles

**Decision**

Performance work for this stage must follow:

1. correctness first
2. contract clarity first
3. cacheable boundaries now
4. reusable runtime/context now
5. no premature CI/precompute dependency
6. no hidden alternate execution path just to hit a benchmark

### 6.3 Required backend shape

**Decision**

The target execution shape remains:

- cold compile/setup once
- hot resolve many times
- reusable compiled state and resolver metadata
- invalidation only for affected families/domains/surfaces
- publication that reads resolved values rather than triggering broad work
- Streamlit reads from sanctioned visible payloads rather than recomputing truth locally

### 6.4 What must be benchmarked for the current stage

**Decision**

Required measurement set:

1. `python -m app.run_stats` or sanctioned equivalent cold run
2. warm rerun in same environment/session where meaningful
3. stats dashboard payload build from prebuilt artifacts where applicable
4. Streamlit-relevant preset switch
5. loadout delta recompute
6. boss-wave table generation
7. max-wave run
8. before/after comparisons for any hot-path change
9. environment notes and repo snapshot metadata

### 6.5 Benchmarking rules

**Decision**

Benchmark claims for this stage must obey:

- measure user-relevant operations, not only broad pipeline totals
- separate cold-start and warm-path costs
- record exact command, repo snapshot, and environment notes
- do not claim structural improvement unless before/after was rerun
- do not count precomputed summary reuse as a compute benchmark unless explicitly labeled as cache benchmark
- do not introduce benchmark-only execution modes unavailable to real users

### 6.6 Performance anti-shortcut rules

**Decision**

Forbidden performance shortcuts:

- Streamlit-local stat math
- publication-local shadow math
- silent precompute dependency for basic correctness
- hidden benchmark-only fast paths
- preserving repeated hot-path naming translation after parity-proven cleanup is available
- broad recompilation on repeated reads where inputs have not changed, once the relevant migration slice is in place

---

## 7. Bloat, residue, and deletion policy

### 7.1 Purpose

**Decision**

“Remove bloat” is not aesthetic cleanup.

It means:
- remove duplicate truth-looking code
- remove stale plausible-looking governance
- remove hot-path drag that confuses AI or slows interactive use
- remove old paths after parity so there is only one active path per concept

### 7.2 What counts as duplicate authority

**Decision**

Examples of duplicate authority for the current program:

- separate kernel spec that appears to outrank or equal the bible
- Streamlit logic that re-derives canonical truth
- publication helpers that repair or invent stat truth
- compat/report logic treated as hot-path primary authority
- stale governance docs treated as active program over live implementation and this bible
- residual alternate simulator paths left looking primary after cutover

### 7.3 Current residue candidates preserved from prior audits

**Verified-imported + Inference**

Residue and blur items from v48 that remain relevant to inspect during this scope:

- stale root governance framing
- hot-path translation and compatibility residue
- Streamlit duplicate module logic
- placeholder/pretend-active files
- overgrown `app/pipeline.py`
- overgrown `evaluators/compare.py` and evaluator residue
- incremental/snapshot/cache residue that may become misleading once a cleaner Streamlit-first simulator path exists

Rule:
- none of these should be removed blindly
- removal or demotion must follow parity or explicit proof of non-use
- but they are in scope where they materially harm truth, speed, or navigability

### 7.4 File-creation restraint

**Decision**

For the current scope:

- prefer editing an existing owner file where ownership is already clear
- new files are allowed only when they make ownership clearer, not blurrier
- no new top-level doc sprawl
- no parallel second-authority markdowns beyond:
  - this active bible
  - the reconciliation review file that audits this bible

### 7.5 Deletion gate

**Decision**

The deletion-first rule after parity remains active:

1. prove parity or non-use
2. cut over the consumer
3. remove or demote the old path
4. update tests and governance
5. do not leave dual primary paths behind

---

## 8. Ordered execution plan for Codex

### 8.1 Program statement

**Decision**

If Codex is told only “continue”, it must execute this program and no broader one:

> Complete the Streamlit-first canonical stat product and deliver the max-waves simulator through that product, with the required performance and residue cleanup to make it trustworthy and usable.

### 8.2 P0: truth protection and scope reset

**Decision**

First actions:

1. Treat this bible as the active authority.
2. Do not follow the stale maintenance-complete tranche as the active implementation program.
3. Re-baseline the latest repo against this scope before widening changes.
4. Explicitly record repo truths that moved since v48, especially the Workshop gap changes.

### 8.3 P1: visible-stat contract activation

**Decision**

Before broad expansion, Codex must make the visible-stat contract active in implementation and tests.

This includes:

- one row contract model
- explicit row statuses
- explicit reconciliation semantics
- explicit provenance rules
- explicit missingness rules
- explicit no-backfill rule
- explicit domain acceptance gate

### 8.4 P2: canonical stat visibility completion

**Decision**

Then complete visible coverage for all current-scope canonical stat domains required for real operator use through Streamlit.

Execution rules:

- Workshop remains the reference pattern
- reuse the same meta-contract across domains
- do not invent bespoke per-domain visibility logic
- do not treat internal scratch variables as mandatory visible rows
- do not leave meaningful canonical stats without a visible home

### 8.5 P3: Streamlit operational product completion

**Decision**

Then complete the Streamlit product surface so the operator can actually use the system rather than just inspect artifacts.

Required outcomes:

- Inputs tab truthfully reflects driving inputs
- Stats tab exposes canonical stat truth with provenance
- Boss Waves / simulator surface exposes the simulator in an operationally useful way
- visible missingness and diagnostics are explicit
- no UI-local repair logic

### 8.6 P4: max-wave simulator delivery

**Decision**

Then finish the current-stage max-wave simulator delivery.

Required outcomes:

- sanctioned run path visible in Streamlit
- max-wave summary visible
- boss-wave table visible
- runtime scenario controls visible and truthful
- tests pass
- simulator semantics remain bounded and explicit

### 8.7 P5: targeted performance hardening

**Decision**

Then harden performance in the way appropriate to this stage:

- remove hot-path translation where justified
- separate cold compile from hot resolve where justified
- reduce repeated broad recompilation
- preserve the sanctioned authority chain
- rerun benchmarks honestly

### 8.8 P6: residue cleanup and governance sync

**Decision**

After truth and performance are in place:

- remove or demote duplicate/stale authority
- update repo governance to match live scope and reality
- ensure no old doc or old path still looks equally primary

### 8.9 Stop rules for blind execution

**Decision**

Stop and report rather than guess if:

- a requested visible surface has unclear owner
- code and current artifacts disagree materially
- simulator semantics would need widening beyond the bounded current survivability contract
- performance claims would rely on hidden benchmark shortcuts
- a cleanup step would delete an apparently live path without parity proof
- evaluator or optimiser work starts to creep back into scope

---

## 9. Acceptance criteria and publish gate

### 9.1 Stats completion gate

**Decision**

The canonical stat visibility program is complete only when:

1. every current-scope canonical user-relevant stat has a visible home in Streamlit
2. each visible row follows the contract
3. each visible row resolves from the sanctioned authority chain
4. missing or non-recon rows are explicitly declared
5. no meaningful stat is being silently backfilled from helper-only data
6. Streamlit is not calculating local truth

### 9.2 Simulator completion gate

**Decision**

The simulator program is complete only when:

1. Streamlit can operate the sanctioned max-wave path
2. max-wave result and boss-wave diagnostics agree
3. runtime controls are explicit
4. current tests covering simulator behavior pass
5. current simulator semantics are explicit and bounded
6. no second active kernel authority remains

### 9.3 Performance gate

**Decision**

Performance is complete for this stage only when:

1. the required benchmark set has been run honestly
2. before/after evidence exists for material performance claims
3. the current hot path reflects cold/hot separation directionally, even if not yet final
4. there is no dependence on hidden precompute or benchmark-only paths
5. current interaction cost is low enough to be practically usable through Streamlit

### 9.4 Cleanup / governance gate

**Decision**

Truthful completion also requires:

- active root governance records no longer misstate the active program, and any preserved historical wording is clearly subordinate to this bible and live implementation reality
- duplicate authority has been removed or explicitly demoted
- no old doc or old execution seam still looks like the primary path for the current scope
- tests and docs materially agree about the completed scope

### 9.5 Canonical verification command set

**Verified-live + Decision**

Minimum command set to use during this program:

- `python -m app.run_stats`
- targeted pytest for touched surfaces
- `pytest tests/app/test_stats_dashboard_contract.py -q`
- `pytest tests/simulators/test_evaluator_kernel.py -q`
- `pytest tests/simulators/test_core_smoke.py -q`
- `pytest tests/simulators/test_boss_waves_parity_shadow.py -q` when Boss Waves product/parity behavior is touched
- broader pytest when a stage claims closure
- inspection of committed outputs relevant to visible query rows and run results

Rule:
- distinguish what was run
- what passed
- what was intentionally not run

---

## 10. Anti-assumptions and refusal rules

### 10.1 Do not infer stale scope

**Decision**

Do not infer from historical governance notes or old completion records that the active work is still only maintenance stabilization. Current root governance is an execution-control companion, not product authority over this Bible.

### 10.2 Do not infer from v48 that the old Workshop gap list is still current truth

**Decision**

The latest repo already appears to have moved on `Interest / Wave` and `Wall Rebuild`, and current thorns naming differs from the older v48 wording.

### 10.3 Do not infer that Streamlit-first means UI-local logic

**Decision**

Streamlit remains the operator surface, not the truth owner.

### 10.4 Do not infer that because evaluator-kernel ideas were good, a second kernel authority should remain

**Decision**

Those ideas are absorbed here. There is no second live kernel spec for the current scope.

### 10.5 Do not infer that because performance matters, CI/precompute must happen now

**Decision**

Current stage performance work must improve the sanctioned hot path first.

### 10.6 Do not infer that because cleanup matters, broad refactor is automatically allowed

**Decision**

Cleanup is in scope only where it reduces authority blur, truth risk, or hot-path drag.

---

## 11. Current one-paragraph summary

**Decision**

The active TowerSim program is now: finish the Streamlit-first canonical stat product, finish the max-waves simulator through that product, keep QE as stat authority and simulators as run authority, preserve explicit provenance and missingness, meet the interactive performance direction already established, and remove duplicate authority or hot-path bloat that would otherwise mislead AI or slow the operator surface.

---

## 12. Appendices

### 12.1 Appendix A: repo delta from v48 baseline

**Verified-live**

Most important delta items confirmed in the latest repo:

- root governance contains active v49 Streamlit-first canonical stat and simulator program records, with historical completion notes and stale maintenance wording still present as context
- current Streamlit already has an operational Boss Waves surface
- `app/pipeline.py` currently wires Boss Waves payloads through `build_boss_wave_payload(...)`
- Boss Waves product behavior uses the replacement path centered on `qe.run_plan`, `simulators.evaluator_kernel`, and `simulators.timing`
- `simulators/run_executor.py` has been removed from the live repo and is not an active compatibility fallback
- simulator tests now cover replacement-kernel rows, timing ownership, Boss Waves product behavior, and parity/certification behavior
- committed query-row artifacts include:
  - `state::economy.interest_per_wave_pct`
  - `state::wall.rebuild_seconds`
  - `state::tower.thorns_damage_pct`

### 12.2 Appendix B: preserved kernel ideas that are now absorbed

**Decision**

Previously separate future-kernel ideas now absorbed into main authority:

- compile/normalize/validate before timed execution
- stable result schema and provenance
- benchmark anti-cheat rules
- cache disclosure rules
- cutover/remove-after-parity rule
- bounded formula-structure guardrails for boss TTK and intake
- hot-path data-layout discipline as direction, not rewrite excuse

### 12.3 Appendix C: benchmark protocol shorthand

**Decision**

Every material performance claim in the current stage should record:

- repo snapshot
- command
- machine/environment notes
- cold/warm distinction
- whether cache was used
- before value
- after value
- what changed

### 12.4 Appendix D: terminology normalization

**Decision**

For the current scope:

- “canonical stat truth” means QE-owned resolved truth
- “visible stat” means operator-visible canonical stat surface
- “max-wave simulator” means the sanctioned simulator path that produces survivability-to-wave outputs for Streamlit
- “bloat” means stale residue, duplicate authority, or unnecessary hot-path drag
- “streamlit-first” means Streamlit is the product surface, not the engine

### 12.5 Appendix E: handoff rule

**Decision**

If Codex is given the repo plus this file and told only “continue”, it must:

1. obey this scope
2. ignore stale maintenance-complete framing where it conflicts with this scope
3. avoid evaluator/optimiser expansion
4. avoid resurrecting a separate kernel authority
5. deliver the Streamlit-first stat and simulator product described here

---
