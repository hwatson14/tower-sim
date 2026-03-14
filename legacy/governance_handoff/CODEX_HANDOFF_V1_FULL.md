# TowerSim Codex Handoff: V1 Canonical Stats Unification

## Purpose
This document is the controlling handoff brief for Codex. It compresses the architecture decisions, repo review findings, failure modes, current roadmap, and the next implementation sequence.

This is not a generic summary. It is the operating brief for continuing the repo safely.

---

## Executive summary
TowerSim is a serious, structured repo with strong contracts and broad tests, but it still has an architecture defect that blocks trustworthy stat correctness:

**static stat truth is split across multiple pipelines.**

The repo currently mixes:
- a canonical-looking static compiler (`tower_sim/engines/stat_input_compiler.py`)
- a survivability-oriented pipeline (`tower_sim/engines/survivability_pipeline.py`)
- an offense/expected-damage-oriented pipeline (`tower_sim/engines/edamage_pipeline.py`)
- orchestration code that sometimes merges outputs from more than one of those paths (`tower_sim/engines/stat_pipeline.py`, `tower_sim/engines/combat_stat_derivation.py`)

This is the root architectural problem. It causes duplicated contributor logic, split ownership, silent drift, and difficulty proving formulas.

The project should **not** have separate truth pipelines for survivability and damage. It should have **one canonical staged stat-construction system** for all stats, with domain evaluators as downstream consumers only.

---

## Locked scope model

### Version roadmap
- **V1**: accurate static stats only
- **V2**: wave progression and timing engine
- **V3**: max wave calculation
- **V4**: optimisers
- **V5**: econ integration and deferred meta systems

### V1 stages
- `baseline_account = workshop coin level + UWs + relics + labs`
- `baseline_gem_respec = baseline_account + bots`
- `baseline_loadout = baseline_gem_respec + cards + modules`

### Explicitly out of scope for V1
- themes
- guardians
- perks
- runtime/timing logic
- free-upgrade progression over waves
- ELS/EHLS progression over waves
- any temporary or triggered effects
- periodic UW or bot overlap effects

### V2 owns
- perk progression
- free upgrades over time
- ELS/EHLS wave progression
- timing engine
- UW timing / uptime / overlaps
- bot timing / uptime / overlaps
- runtime mutation of stats at wave or event time

### V5 owns
- themes
- guardians
- econ/meta systems

---

## Architecture target

### Desired system shape
1. **One canonical staged stat-construction layer**
   - baseline_account
   - baseline_gem_respec
   - baseline_loadout
   - later: at_wave (V2)

2. **One runtime progression layer**
   - free upgrades
   - perks
   - wave-state mutation
   - timing / uptime / overlap systems

3. **Domain evaluators as consumers only**
   - survivability
   - edamage / offense
   - max wave
   - optimiser
   - econ

### Canonical ownership rule
For every stat there must be:
- one canonical owner
- one first stage of construction
- one contributor ledger
- downstream consumers may consume it, not redefine it

### File-role target
#### Canonical owners
- `tower_sim/engines/stat_input_compiler.py`
- `tower_sim/engines/stat_pipeline.py`
- `tower_sim/engines/statbook_builder.py`
- `tower_sim/engines/stat_engine.py` only where it resolves canonical stats rather than introducing another truth path

#### Runtime mutators
- `tower_sim/engines/combat_stat_derivation.py`
- wave/perk/uptime/free-upgrade helpers in V2

#### Consumers only
- `tower_sim/engines/survivability_pipeline.py`
- `tower_sim/engines/edamage_pipeline.py`

### What must stop happening
- `survivability_pipeline.py` rebuilding static base/loadout stats
- `edamage_pipeline.py` rebuilding static base/loadout stats
- orchestration code merging multiple static truth paths
- any stat depending on which pipeline you happened to call

---

## What has gone wrong so far

### 1. Use-case pipelines were allowed to become truth pipelines
The repo evolved around solving local use cases (survivability, edamage, max-wave) rather than enforcing one stat truth layer first.

Result:
- duplicate stat assembly
- split contributor wiring
- consumers acting like owners
- complicated compensating logic in orchestration

### 2. Static loadout truth is still split
Current review indicates:
- `stat_input_compiler.py` already owns a lot of static truth: workshop, labs, UWs, relics, bots
- cards/modules still appear heavily owned from domain pipelines
- survivability/offense paths still assemble overlapping static stats

### 3. Stage boundaries were implicit instead of executable
Originally there was no clean executable distinction between:
- baseline_account
- baseline_gem_respec
- baseline_loadout

This made it easy for contributor families to leak into the wrong stage.

### 4. Formula verification discipline was not tight enough
A major process rule from the user is:
- **all formula changes must be with reference to the wiki**

This requirement was not enforced tightly enough in the earlier loop. Implementation should now require formula-source verification before code changes that affect stat math.

### 5. At least one important stat family was implemented with wrong semantics
The clearest concrete bug identified was in wall stat handling.

---

## Confirmed concrete issue found in review

### Wall stat semantics bug
In `tower_sim/engines/stat_input_compiler.py`, `Wall Health` and `Wall Regen` were being treated too much like generic workshop stats with lab multipliers, then also re-derived through wall alias logic.

That created a semantic problem and a likely double-counting problem:
- generic workshop/lab handling was mutating the wall workshop ratio too early
- then wall alias derivation also applied wall-specific lab logic

The smallest corrective move that was made in the working thread was:
- treat `Wall Health` and `Wall Regen` like lab-delta stats for canonical handling
- prevent the generic workshop delta path from directly mutating emitted workshop wall ratios
- keep wall-specific lab effects in derived wall alias construction instead of generic workshop stat multiplication

This was the first surgical fix because it had strong wiki grounding and was isolated enough to patch safely.

Note: this thread’s local working copy had a patch and regression tests around the wall issue, but the main value for Codex is the architectural lesson: **ratio-derived stats need explicit algebra and contributor staging, not generic multiplier treatment.**

---

## High-confidence repo review findings

### Strengths
- strong contract spine: `CONTRACT.md`, `REPO_MAP.yaml`, `README.md`
- broad test surface
- clear repo intent around determinism, provenance, and fail-closed behavior
- `stat_input_compiler.py` is already a natural canonical owner candidate

### Weaknesses / risks
1. split stat truth across canonical and domain pipelines
2. overly large central files with mixed responsibilities
3. some fail-closed softness through degradation/exception handling rather than hard-stop
4. stale status/history sediment in docs
5. hidden contributor logic may still exist inside domain helpers

### Most important architectural diagnosis
The repo is **not fundamentally broken**, but it is at risk of becoming a two-spine system:
- one canonical static path
- one or more parallel domain-specific static paths

That must be collapsed into one spine.

---

## Current migration status from this thread

### Architecture decisions already locked
- one canonical staged static stat-construction system
- no survivability-specific truth layer
- no edamage-specific truth layer
- cards and modules belong in canonical `baseline_loadout`
- bots are static-only in V1
- UWs are static always-on only in V1
- perks are excluded from V1
- compatibility wrappers are allowed temporarily if they do not own truth
- minimal new files; prefer editing existing files
- themes and guardians moved to V5

### Work already begun in thread-local working copy
- explicit stage wrappers were introduced conceptually / locally for:
  - `compile_baseline_account_inputs(...)`
  - `compile_baseline_gem_respec_inputs(...)`
- `compile_full_stat_inputs(...)` was demoted to a compatibility wrapper over the gem-respec stage
- wall lab semantics were patched locally with targeted tests in the working thread environment

Do not assume those local patches are the final answer. Use the architecture and problem framing first, then confirm/implement cleanly in the Codex branch.

---

## Required implementation posture

### Non-negotiable rules
1. **No rebuild**
   - This is a surgical unification effort, not a repo redesign.

2. **Minimal file creation**
   - Prefer editing existing owners.
   - New files only if absolutely necessary and clearly justified.

3. **All formula-affecting changes must be verified against the wiki first**
   - source-check before code change
   - cite/record the formula source in commit/PR/checkpoint notes

4. **Every patch must preserve the canonical ownership goal**
   - if a stat is assembled in more than one place, one place must lose

5. **Every checkpoint must update status**
   - what changed
   - tests run
   - risks remaining
   - next checkpoint

---

## Recommended immediate roadmap

### Phase 0: stabilize the architecture in code
Goal: make staged ownership explicit.

Tasks:
- ensure `stat_input_compiler.py` exposes:
  - `compile_baseline_account_inputs(...)`
  - `compile_baseline_gem_respec_inputs(...)`
  - `compile_baseline_loadout_inputs(...)`
- keep `compile_full_stat_inputs(...)` only as temporary compatibility wrapper

### Phase 1: canonicalize all static stat families
Goal: build one static statbook for all V1 stats.

Tasks:
- map all relevant canonical stat IDs
- identify first stage for each stat
- define contributor families and algebra mode per family
- move static card contributions into canonical `baseline_loadout`
- move static module main + substat contributions into canonical `baseline_loadout`

### Phase 2: demote domain truth ownership
Goal: survivability and edamage become consumers only.

Tasks:
- remove/bypass static stat assembly from `survivability_pipeline.py`
- remove/bypass static stat assembly from `edamage_pipeline.py`
- update `stat_pipeline.py` and `combat_stat_derivation.py` to stop merging parallel static paths

### Phase 3: clean orchestration and guardrails
Goal: one canonical source flows cleanly through the repo.

Tasks:
- simplify orchestration imports/calls
- tighten tests around stage ownership and contributor coverage
- ensure runtime code only mutates V2+ state, not V1 truth

### Phase 4: extend formula verification ledger
Goal: make future changes safer.

Tasks:
- build formula ledger for canonical stats
- each stat entry should record:
  - first stage
  - formula owner
  - contributor families
  - algebra mode
  - wiki/table source

---

## Specific repo files most relevant to the work

### Control / architecture docs
- `CONTRACT.md`
- `REPO_MAP.yaml`
- `README.md`
- `IMPLEMENTATION_STATUS.md`
- `mechanics/canonical_mechanics_contract.md`
- `mechanics/manifest.yaml`

### Core canonical stat construction
- `tower_sim/engines/stat_input_compiler.py`
- `tower_sim/engines/stat_pipeline.py`
- `tower_sim/engines/stat_engine.py`
- `tower_sim/engines/statbook_builder.py`
- `tower_sim/engines/combat_stat_derivation.py`

### Domain pipelines that need demotion
- `tower_sim/engines/survivability_pipeline.py`
- `tower_sim/engines/edamage_pipeline.py`
- `tower_sim/engines/edamage_formulas.py`
- `tower_sim/engines/modules.py`

### Registry and naming/contracts
- `tower_sim/registry/stat_registry.py`
- `tower_sim/registry/combat_stat_contract.py`
- `tower_sim/registry/naming_contract.py`
- `tower_sim/registry/identifier_resolver.py`

### Source tables/libraries likely relevant to contributor wiring
- `tower_sim/libs/cards_lib.py`
- `tower_sim/libs/modules_lib.py`
- `tower_sim/libs/module_main_effects.py`
- `tower_sim/libs/bots_lib.py`
- `tower_sim/libs/uw_lib.py`
- `tower_sim/libs/labs_lib.py`
- `tower_sim/libs/workshop_lib.py`

### Snapshot / source compilation
- `tower_sim/loaders/account_snapshot_compiler.py`
- `tower_sim/loaders/account_snapshot_loader.py`
- `tower_sim/loaders/ids_parser.py`
- `tower_sim/util/account_snapshot.py`
- `tower_sim/util/statbook.py`

### Tests most relevant to this migration
- `tests/test_stat_input_compiler.py`
- `tests/test_stat_pipeline.py`
- `tests/test_stat_pipeline_guardrails.py`
- `tests/test_stat_engine.py`
- `tests/test_statbook_builder.py`
- `tests/test_canonical_statbook.py`
- `tests/test_combat_stat_derivation.py`
- `tests/test_survivability_pipeline.py`
- `tests/test_edamage_pipeline.py`
- `tests/test_edamage_formulas_registry_routing.py`
- `tests/test_cards_lib.py`
- `tests/test_modules_lib.py`
- `tests/test_module_main_effects.py`
- `tests/test_bots_lib.py`
- `tests/test_uw_lib.py`
- `tests/test_labs_lib.py`
- `tests/test_workshop_lib.py`
- `tests/test_stat_registry.py`
- `tests/test_naming_contract.py`
- `tests/test_stat_source_coverage.py`
- `tests/test_canonical_derivation_source_coverage.py`

---

## What Codex should do first

1. Read this file and `legacy/governance_handoff/STATUS_V1.yaml`
2. Inspect the current canonical owner files and confirm the stage wrappers / current state
3. Confirm whether the wall patch from the thread-local work is already present in the target branch; if not, re-derive and apply it cleanly with tests
4. Implement canonical `baseline_loadout` in `stat_input_compiler.py`
   - cards first
   - modules second
5. Demote duplicate static ownership in `survivability_pipeline.py` and `edamage_pipeline.py`
6. Update `stat_pipeline.py` / `combat_stat_derivation.py` so they stop compensating for split static ownership
7. For every formula-affecting change:
   - verify against wiki first
   - record the source in checkpoint notes

---

## What not to let Codex do
- create a new parallel “unified pipeline” file
- create new special-case survivability stat models
- keep both canonical and domain-specific static assembly “for flexibility”
- expand V1 to include V2 timing/perks/runtime behavior
- move themes/guardians back into V1
- silently change algebra without source verification

---

## Success criteria for V1 closure
V1 is only done when:
- every static stat is built from one canonical staged path
- cards and modules are canonical `baseline_loadout` contributors
- survivability/edamage pipelines no longer own static truth
- orchestration no longer merges parallel static paths
- formula-affecting changes are source-backed
- the resulting static statbook is trustworthy enough to support V2 progression without re-litigating baseline truth

