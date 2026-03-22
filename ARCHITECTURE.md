# Architecture

This document defines the architectural intent for the TowerSim repo. It describes both what currently exists and the target layering that Codex should build toward.

Every architectural choice must respect the KB-alignment rule: if the Knowledge Base defines a mechanic, the code must implement that mechanic or explicitly declare a temporary accepted model. Code is never self-justifying proof of mechanic truth.

This document follows the canonical planning vocabulary from `AI_EXECUTION_PLAN.md`. No separate roadmap file should be treated as competing execution truth or as required planning authority.

---

## The Six Layers

TowerSim is organised around six canonical layers. Each layer depends only on layers above it.

```
┌─────────────────────────────────────────────────┐
│  Knowledge Base                                  │
│  What is mechanically true about the game?       │
├─────────────────────────────────────────────────┤
│  Inputs                                          │
│  What does this player have?                     │
├─────────────────────────────────────────────────┤
│  Query Engine                                    │
│  What is stat X for player Y in scenario Z?      │
├─────────────────────────────────────────────────┤
│  Simulators                                      │
│  What is likely to happen from this state?       │
├─────────────────────────────────────────────────┤
│  Optimisers                                      │
│  What should I upgrade next?                     │
├─────────────────────────────────────────────────┤
│  Advisors                                        │
│  What should my strategy be?                     │
└─────────────────────────────────────────────────┘
```

Dependency flows downward only. Advisors may consume from any layer above. Optimisers consume from the Query Engine and Simulator surfaces but never modify them. The Query Engine reads the KB and Inputs but does not depend on Simulators, Optimisers, or Advisors.

Runtime and event-model simulators in `engine/` are the canonical Simulator layer for this repo. No alternate layer name should be inferred from earlier roadmap wording.

---

## Layer Definitions

### 1. Knowledge Base

**Question it answers:** What is mechanically true about the game?

**Scope:** Formulas, stat composition rules, contributor routing, scaling curves, timing contracts, scenario rules, runtime ordering, mechanic ownership, strategy frameworks, and advisory reasoning content. Everything that is true about the game independent of any particular player account.

**Ownership rule:** The KB is the single source of mechanic truth. No other layer may define, override, or silently reinterpret game mechanics. If a mechanic is not represented in the KB, it must be added to the KB before code implements it — or the code must be explicitly labelled as a temporary accepted model.

**Internal structure:** The KB is organised by game domain, each with a consistent internal pattern:

```
kb/{domain}/
    contracts/     Runtime and application contracts (the KB-to-code API)
    kb/<domain>/tables/  Canonical data tables (the primary query surface)
    notes/         Explanatory context (human consumption, not code)
    sources/       Provenance and evidence (grounding, not code)
    derived/       Materialised views (computed from tables, not primary)
```

`kb/advisory/` contains strategy, reasoning, and prompt content consumed by the Advisors layer. This is game knowledge about how to play well, not mechanic definitions. It lives in the KB because it is knowledge, but it is consumed by Advisors, not by the Query Engine.

**Current state:** Complete and stable. 637 files across 17 domain subdirectories. This is the strongest part of the repo.

**Where the code lives:** `kb/` (no Python code — pure data, contracts, and documentation)

---

### 2. Inputs

**Question it answers:** What does this player have?

**Scope:** Parsing raw game exports, compiling account state, resolving loadout and perk selections, managing state modes. Produces a fully resolved `AccountState` that downstream layers consume.

**Ownership rule:** Inputs owns the translation from raw game data into structured account state. It does not own mechanics, formulas, or stat resolution. It reads KB routing policy to know where to send contributor values, but it does not resolve final stat values — that is the Query Engine's job.

**Current state:** Functional. The main architectural debt is that `stat_input_compiler.py` straddles this layer and the Query Engine: its input-compilation half belongs here, its KB-routing half belongs in the Query Engine. The R86 baseline materialiser work will resolve this straddling.

**Where the code lives:**

| File | Lines | Role |
|---|---|---|
| `parsers/ids_parser.py` | 101 | Parse raw IDS CSV export into structured sections |
| `compilers/account_state_compiler.py` | 534 | Build AccountState from parsed IDS + loadout + perk config |
| `compilers/stat_input_compiler.py` | 2,135 | Compile stat input rows (straddles Inputs and Query Engine — see note above) |
| `models/account_state.py` | 118 | AccountState data model |
| `models/ids_raw.py` | 13 | Raw IDS data model |
| `models/stat_input.py` | 26 | StatInput data model |

**Input data:** `input/` directory (IDS export, loadout config, perk config, EP export)

---

### 3. Query Engine

**Question it answers:** What is stat X for player Y in scenario Z?

**Scope:** Deterministic stat resolution. Given an account state, a scenario, and a state mode, resolve any canonical stat surface to a final value with full contributor trace. The Query Engine is the canonical authority for "what are the numbers?" — it is a function from (account state, scenario, query) to (answer with provenance).

**Ownership rule:** One stat, one resolution path, one owner. The Query Engine must produce identical results for identical inputs. It must never silently cache, approximate, or re-derive a surface that it has already resolved. Contributor-ledger visibility is a first-class requirement: every resolved stat must be traceable to its contributing sources.

**Current state:** The core resolver exists and works (`stat_engine.py`), and the phase-1 query API primitives now exist in `engine/state_identity.py`, `engine/family_baseline_materializer.py`, and `engine/stat_query_kernel.py`. Timing-family query execution is already wired through this bounded API. The bounded progression recalc bridge now routes its runtime/reference path through declared query-owned families, but the broader R86 acceptance thread is still open: global parity validation across declared families, end-to-end overlay/invalidation closure, Gate F benchmark evidence, and the remaining KB-routing ownership extraction are still pending acceptance evidence rather than requiring a redo of the landed bridge migration.

**Key interfaces:**
- Consumes: `AccountState` from Inputs, mechanic contracts and tables from the KB
- Produces: `StatBook` (resolved stat values with contributor traces), scenario-aware query responses

**Where the code lives:**

| File | Lines | Role |
|---|---|---|
| `engine/stat_engine.py` | ~13 | Legacy compatibility entrypoint that re-exports the canonical resolver surface |
| `engine/stat_resolution_core.py` | ~1,500 | Core stat resolution — the heart of this layer |
| `engine/scenario_engine.py` | 537 | Scenario configuration and scenario-dependent surface handling |
| `engine/scenario_runtime_inputs.py` | 90 | Scenario input assembly |
| `engine/derived_surface_composer.py` | 156 | Derived stat composition |
| `engine/dependency_registry.py` | 107 | Progression dependency DAG |
| `engine/state_identity.py` | 145 | Account/loadout/scenario/runtime-branch identity binding for bounded queries |
| `engine/family_baseline_materializer.py` | 340 | Family-scoped baseline contributor materialisation from routed stat inputs |
| `engine/stat_query_kernel.py` | 420 | Bounded query API kernel for baseline resolution, overlays, and trace output |
| `models/statbook.py` | 28 | StatBook output data model |

**Planned (post-R86):** Continue moving primary orchestration onto the bounded query API surface and use the existing contract/test stack to extend bounded family coverage deliberately. See `kb/global-rules/contracts/stat-query-*.yaml` for the contract definitions.

---

### 4. Simulators

**Question they answer:** What is likely to happen from this state?

**Scope:** Deterministic or governed runtime models built from Query Engine truth plus event-model simulation. Simulators cover wave progression, boss encounters, run timing, survivability modelling, wall-contact geometry, workshop upgrade progression, perk timeline projection, and incremental recalculation.

**Distinction from the Query Engine:** The Query Engine resolves "what is Tower Damage right now?" — a static, deterministic answer. A Simulator answers "how many waves does the tower survive?" or "how long until wave 1000?" — questions that require modelling sequences of events, interactions between stats, and temporal dynamics.

**Ownership rule:** Simulators own runtime-model surfaces for a modelling domain. They consume Query Engine outputs as their input parameters. They do not re-derive stats, re-route contributors, or bypass the Query Engine. If a simulator needs a stat value, it asks the Query Engine.

**Current state:** Multiple simulator subsystems already exist in various stages of maturity. The boss wave engine and timing engine are the most complete. The geometry pipeline is structurally complete but out of scope for Phase 1 extension. The incremental recalc subsystem optimises repeated simulation runs. Several simulation-adjacent functions currently live inside `run_stats.py` as gap/closure/residue reports — these are candidates for later extraction into cleaner simulator surfaces.

**Implementation note:** Earlier planning text used alternate naming for this layer. That wording is retired. Simulator is the canonical layer name across the repo.

**Where the code lives:**

| Subsystem | Files | Lines | Maturity |
|---|---|---|---|
| Boss wave engine | `engine/boss_wave_engine.py` | 979 | Active simulator subsystem |
| Timing engine | `engine/timing_engine.py` | 453 | Active simulator subsystem |
| Wave progression | `engine/wave_progression_policy.py` | 78 | Active simulator policy |
| Geometry wall-contact | `engine/geometry_wall_contact_*.py` (10 files) | ~780 | Structurally complete; Phase 1 out of scope |
| Workshop progression | `engine/progression_state.py`, `engine/workshop_progression_policy.py`, `engine/free_upgrade_generation_policy.py` | ~414 | Active simulator subsystem |
| Perk timeline | `engine/perk_timeline_generator.py`, `engine/perk_timeline_state.py`, `engine/perk_tables.py` | ~280 | Active simulator subsystem |
| Incremental recalc | `engine/incremental_*.py` (6 files), `engine/progression_recalc_bridge.py` | ~713 | Active optimisation support |
| Runtime consumers | `engine/runtime_consumer_executor.py`, `engine/runtime_consumer_registry.py` | ~96 | Active simulator plumbing |
| Gap/residue analysis | Functions in `run_stats.py` | ~1,400 | Embedded; candidates for future extraction |

---

### 5. Optimisers

**Question they answer:** What should I upgrade next?

**Scope:** Sensitivity analysis, marginal-value scoring, upgrade path ranking, resource allocation evaluation. Given the current state of an account and a defined objective, identify which action produces the greatest improvement per unit of cost.

**Distinction from Simulators:** A Simulator models what is likely to happen. An Optimiser evaluates what should be done. Optimisers consume Simulator outputs (projected outcomes) and Query Engine outputs (current stats) and score candidate actions against defined objectives.

**Ownership rule:** Each optimiser owns a specific objective function or family of objectives. Optimisers are consumers, not producers, of mechanic truth. They do not define formulas or modify stats. They score and rank.

**Current state:** A working scorer and path ranker exist, reverse-engineered against the EP v5.03.02 spreadsheet. Documented accuracy gaps exist in eDamage (missing UW damage channels) and eEcon (missing economy terms). As the Query Engine and simulator subsystems mature, the Optimiser input surface becomes richer and more accurate.

**Planned evolution:** Multiple optimisers for different objective families — survivability optimisation, economy optimisation, tournament optimisation, balanced multi-objective optimisation. Each consumes different simulator outputs and weights objectives differently.

**Where the code lives:**

| File | Lines | Role |
|---|---|---|
| `optimizer/scorer.py` | 171 | eHP/eDamage/eEcon sensitivity scoring |
| `optimizer/path_ranker.py` | 113 | Upgrade path ranking |
| `optimizer/ACCURACY.md` | — | Honest accuracy gap documentation |

---

### 6. Advisors

**Question they answer:** What should my strategy be?

**Scope:** Strategic reasoning, build planning, progression planning, tournament preparation, resource allocation across time horizons. Where an Optimiser answers "upgrade X next," an Advisor answers "here is a coherent plan for the next two weeks that accounts for your tournament schedule, stone budget, and progression targets."

**Distinction from Optimisers:** An Optimiser is a scoring function — it evaluates and ranks. An Advisor is a reasoning system — it synthesises across multiple objectives, constraints, timelines, and context to produce strategic guidance. Advisors may invoke multiple Optimisers, Simulators, and Query Engine calls to construct their reasoning.

**Ownership rule:** Advisory knowledge (strategy frameworks, reasoning playbooks, meta-models) lives in the KB at `kb/advisory/`. Advisory code (planners, recommenders, strategy engines) lives in the Advisors layer. The split is the same as everywhere else: knowledge in the KB, code in its layer.

**Current state:** Knowledge-only. The advisory content in `kb/advisory/` is well-developed:
- `kb/advisory/strategy/` — 17 strategy documents covering build models, tournament meta, economy analysis, progression models
- `kb/advisory/reasoning/` — 7 reasoning frameworks and playbooks
- `kb/advisory/prompts/` — 4 files defining how an AI advisor should use the KB (system prompt, diagnosis subprompt, optimisation subprompt, retrieval map)

No advisory code exists yet. The prompts and frameworks currently serve as instructions for ChatGPT sessions. As the repo matures, advisory code will be written that programmatically applies these reasoning patterns.

**Planned evolution:** Planners (multi-step strategy generation), build advisors (account-specific guidance), tournament preparation advisors (BC-aware build adjustment), progression planners (long-horizon stone and upgrade allocation).

**Where the code will live:** `advisors/` (does not yet exist)

**Where the knowledge lives:** `kb/advisory/` (already populated)

---

## Current Pipeline

The canonical execution path through the current code:

```
python run_stats.py
    │
    ├── parsers/ids_parser.py              [Inputs]
    │     Parse raw IDS CSV → structured sections
    │
    ├── compilers/account_state_compiler.py [Inputs]
    │     IDS + loadout + perks → AccountState
    │
    ├── compilers/stat_input_compiler.py    [Inputs → Query Engine]
    │     AccountState → list of StatInput rows
    │     (straddles: input compilation + KB routing)
    │
    ├── engine/stat_engine.py              [Query Engine]
    │     StatInput rows → StatBook (resolved stats)
    │
    ├── optimizer/scorer.py                [Optimisers]
    │     StatBook → eHP/eDamage/eEcon scores
    │
    └── run_stats.py itself                [Orchestration + embedded concerns]
          EP oracle comparison
          Gap/closure/residue analysis
          Display formatting
          Audit construction
          Output serialisation
```

`run_stats.py` is 3,066 lines because it currently owns orchestration plus ~2,000 lines of embedded verification, analysis, and formatting concerns. These will eventually migrate into their proper layers as the architecture matures. This is a known debt, not a surprise.

---

## Architectural Boundaries and Seams

### Clean boundaries (respect these)

- **KB → everything:** All layers read from the KB. No layer writes to the KB at runtime.
- **Inputs → Query Engine:** Inputs produces an `AccountState`; the Query Engine consumes it. This boundary is well-defined.
- **Query Engine → Simulators/Optimisers:** The Query Engine produces canonical truth consumed directly by current optimisers and by simulator subsystems.

### Active seams (resolve these over time)

- **`stat_input_compiler.py` straddles Inputs and Query Engine.** The R86 baseline materialiser extracts the KB-routing concern into the Query Engine. This is the highest-priority seam.
- **`engine/` is flat.** Query Engine files, simulator subsystems, and perk timeline files all live in one directory. As the Query Engine gets its own API surface (R86), the natural split point will emerge. Do not force a premature directory restructure — let the code boundaries drive it.
- **`run_stats.py` touches all layers.** It will shrink as each layer gets a proper API. The eventual target is a thin orchestrator that calls layer APIs in sequence.

### Future boundaries (do not build yet)

- **Advisors layer code does not exist.** The advisory knowledge is in the KB; the code layer is future work. When it arrives, it will be `advisors/` consuming from `kb/advisory/`, Query Engine, Simulators, and Optimisers.
- **Multiple Optimiser modules.** Currently `optimizer/` is a single scorer + ranker. Future optimisers (survivability, economy, tournament, multi-objective) will be additional modules in this package.

---

## Where New Code Goes

| I am building... | It goes in... | It consumes from... |
|---|---|---|
| A new game mechanic formula | `kb/` (as a contract or table) | Nothing — it is consumed |
| A new input parser or account compilation step | `parsers/` or `compilers/` | KB routing contracts |
| A new stat resolution path or query surface | `engine/` (Query Engine subset) | KB contracts, Inputs |
| A new runtime model or forecast surface (timing, waves, survivability) | `engine/` (Simulator subset) | Query Engine outputs |
| A new objective scorer or path ranker | `optimizer/` | Query Engine, Simulators |
| A new planner, strategy engine, or advisory tool | `advisors/` | KB advisory content, Query Engine, Simulators, Optimisers |
| Strategy knowledge, reasoning frameworks, meta-models | `kb/advisory/` | Nothing — it is consumed |

---

## Constraints

### Dependency direction is enforced

No layer may depend on a layer below it in the stack. Specifically:
- The KB depends on nothing
- Inputs reads KB contracts but does not depend on the Query Engine, Simulators, Optimisers, or Advisors
- The Query Engine reads the KB and Inputs but does not depend on Simulators, Optimisers, or Advisors
- Simulators consume Query Engine outputs but do not depend on Optimisers or Advisors
- Optimisers consume Query Engine and Simulator outputs but do not depend on Advisors
- Advisors may consume from any layer above

### One mechanic, one owner

Every game mechanic has exactly one canonical implementation. No parallel formulas, shadow calculation paths, or convenience re-derivations that bypass the owning layer. If two pieces of code compute the same thing, one of them is wrong.

### KB alignment is non-negotiable

If the KB defines a mechanic, the code must implement that mechanic. If the code disagrees with the KB, the code has a defect — not the KB. The only exception is an explicitly declared temporary accepted model, which must be labelled, scoped, and documented for later replacement.

### Honest incompleteness over fabricated completion

If a layer cannot answer a question, it should say so clearly rather than approximate silently. An unanswered query with an honest "not yet implemented" is better than a wrong answer that appears authoritative.
