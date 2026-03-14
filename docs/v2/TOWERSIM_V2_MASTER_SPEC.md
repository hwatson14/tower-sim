# TowerSim V2 Master Spec

## 1. Purpose

This document is the authoritative implementation specification for TowerSim V2.

Its purpose is to define one deterministic, contributor-centric, fail-closed architecture for building the simulator from canonical source state through resolved stats to runtime evaluation.

This spec exists to prevent:
- naming drift,
- stage drift,
- evaluator-specific stat handling,
- composite ownership leakage,
- silent inheritance of V1 ambiguity.

This spec is authoritative for V2 implementation unless explicitly superseded by `CONTRACT.md`.

## 2. Authority order

When sources disagree, authority order is:

1. `CONTRACT.md`
2. approved handover / ledger contract documents in `audit/reference/tower_sim_3_handover/`
3. approved naming plan / ledger normalization docs in `audit/`
4. V2 registries generated under this spec
5. V2 code
6. V1 code and registries
7. ad hoc implementation assumptions

V1 is never an authority for canonical naming or contributor semantics merely because code exists.

## 3. Core principles

### 3.1 All stats at once, by layer
V2 must be rebuilt horizontally by architectural layer, not vertically by evaluator.

Forbidden approach:
- survivability-first stat rebuild
- econ-first stat rebuild
- max-wave-first stat rebuild

Required approach:
- source normalization for all relevant static systems
- contributor emission for all relevant static systems
- target resolution for all relevant static target stats
- derived static resolution
- runtime overlays
- evaluator consumption

### 3.2 Contributor-centric
One row = one real contributor from one contributor family affecting one target stat through one explicit operation.

A row is not allowed to represent:
- an already-merged composite value
- a stage placeholder
- a fabricated helper identity
- an evaluator-local convenience variable

### 3.3 Composite ownership is central, not local
Composite or multi-source stats must be resolved in the central V2 resolver layer.

No evaluator, adapter, or loader may privately own the meaning of:
- health
- wall_health
- wall_regen
- defense_pct
- other composite/static-dependent targets

### 3.4 Fail-closed
Unknown naming, unmapped contributors, mixed domains, or unsupported semantics must stop or quarantine explicitly.

Silent fallback is forbidden.

### 3.5 Canonical names flow inward
Canonical names are the authority.
Legacy names may be translated at adapters or alias boundaries only.

Canonical names must never be rewritten into legacy names inside the V2 contract core.

## 4. Name domains

Every identifier in V2 must belong to exactly one primary domain:

1. canonical_target_stat
2. canonical_contributor_id
3. source_state_field
4. derived_stat
5. runtime_state_field
6. report_or_audit_field
7. table_or_config_symbol
8. implementation_artifact
9. approved_alias
10. legacy_or_unresolved

No identifier may be used across domains without an explicit mapping rule.

## 5. Stage model

### 5.1 Static stages
The static pipeline has exactly these first-class stages:

1. `baseline_account`
   - static account baseline before gem-respec-coupled or loadout-coupled additions

2. `baseline_gem_respec`
   - baseline plus gem-respec-coupled static contributors
   - explicitly includes systems whose static effects depend on post-respec account state

3. `baseline_loadout`
   - loadout-dependent static contributors
   - cards, modules, and other selected-in-run static effects

### 5.2 Runtime overlays
The following are not part of the static kernel:
- wave progression
- perk timeline progression
- runtime toggles
- cooldown/runtime activation state
- combat state
- boss fight state
- at-wave dynamic overlays

These belong to later runtime layers.

### 5.3 Wave progression relationship
Wave progression is not a static stage.
Wave progression is a runtime overlay input surface that consumes resolved static baselines and applies dynamic/wave-index-dependent logic after static resolution.

## 6. V2 architecture layers

### Layer 1: reference and contract
Defines:
- canonical target stat registry
- canonical contributor registry
- alias registry
- stage applicability registry
- contributor family registry
- operation semantics registry
- composite dependency registry
- runtime deny-list

### Layer 2: source-state normalization
Input adapters convert raw repo/user/source data into normalized source-state records.

Source-state records are not contributor rows.

Examples of source-state families:
- workshop
- labs
- relics
- cards
- modules main effects
- module substats
- module unique effects
- ultimate weapons
- ultimate weapon plus
- bots
- perks
- battle conditions
- guardians
- vault / enhancement / other approved systems

### Layer 3: contributor emission
Normalized source-state is converted into canonical contributor rows.

Contributor row fields:
- contributor_id
- contributor_family
- target_stat
- operation
- value
- stage
- source_ref
- provenance
- confidence / mapping status if required for migration

A contributor row must correspond to a real semantic contributor, not a merged stat result.

### Layer 4: static target resolution
All static target stats are resolved in one pass from contributor rows.

Responsibilities:
- operation ordering
- additive / multiplicative / override semantics
- caps and bounded stats
- stage-aware inclusion
- target dependency ordering

### Layer 5: derived static resolution
Resolves static derived stats that depend on previously resolved static targets.

Examples:
- wall_health from tower health plus wall rules
- wall_regen from tower regen plus wall rules
- explicit derived stats defined by formula registry

### Layer 6: runtime overlay layer
Applies wave, perk, combat, boss, and other runtime mechanics over resolved static outputs.

### Layer 7: evaluator layer
Max-wave, survivability, econ, and other evaluators consume V2 outputs through stable interfaces.

## 7. Canonical artifacts required

The following artifacts must exist and be authoritative for V2:

1. `v2_canonical_target_stats`
2. `v2_mechanic_parameters`
3. `v2_environment_parameters`
4. `v2_capabilities`
5. `v2_contributor_ids`
6. `v2_alias_map`
7. `v2_source_state_schema`
8. `v2_stage_applicability`
9. `v2_contributor_operations`
10. `v2_composite_dependencies`
11. `v2_runtime_field_registry`
12. `v2_quarantine_registry` for explicitly tolerated migration exceptions

Object-class boundary rule:
- canonical target stats, mechanic parameters, environment parameters, and capabilities are distinct registry classes and must not be collapsed into one undifferentiated "canonical stats" bucket.

These should be machine-readable where practical.

## 8. Contributor semantics

### 8.1 Allowed operation classes
Operations must be explicit and registry-defined. Example classes include:
- set_base
- add
- multiply
- set_cap
- set_flag
- set_derived
- reduce_cooldown
- set_duration
- set_count
- set_range
- other approved domain-specific operations

The allowed operation for each contributor_id is defined by the contributor registry, not inferred ad hoc.

### 8.2 Target ownership
Every contributor_id must declare:
- exactly which target_stat it affects
- operation type
- stage applicability
- contributor family
- whether it is direct or feeds a derived dependency

### 8.3 No fabricated contributor IDs
Contributor IDs like:
- `legacy_stage__...`
- `resolved__...`
- `helper__...`
- stage-local synthetic contributor placeholders

are forbidden as canonical contributor IDs.

Legacy mapping may exist in adapters or quarantine registries, but not as the canonical V2 contributor model.

## 9. Composite and dependent stat rules

### 9.1 Composite targets
Composite targets are target stats with more than one direct contributor family or which depend on other resolved target stats.

Examples likely include:
- health
- wall_health
- wall_regen
- defense_pct
- damage
- health_regen
- other multi-source targets

### 9.2 Required rule
Composite targets must be resolved centrally from canonical contributor rows and explicit dependency rules.

### 9.3 Forbidden rule
No loader, evaluator, or local helper may privately redefine the meaning of a composite stat.

## 10. Naming enforcement

### 10.1 Canonical direction
Canonical target and contributor names are the only authoritative internal names for V2.

### 10.2 Alias handling
Aliases are allowed only when:
- explicitly declared in `v2_alias_map`
- one-way toward canonical names
- justified by migration needs

Example direction:
- legacy -> canonical

Forbidden direction:
- canonical -> legacy as an internal contract rule

### 10.3 Runtime/static separation
Runtime fields must not appear in static registries or static target resolution.

Static pipeline must reject runtime-only identifiers such as wave-index fields and combat-state fields.

### 10.4 Canonical target ID normalization guardrails (V2)
For V2 canonical target IDs, prefer one runtime-facing parameter per semantic concept.

Required guardrails:
- do not register duplicate semantic IDs for the same concept (example collision: `*.quantity` vs `*.count`)
- do not register source-surface aliases as canonical IDs (`tower_hp` vs `tower_health` must converge to one canonical target)
- reserve flat `tower_*` IDs for tower-level canonical targets; do not place subsystem mechanic parameters in canonical target stat registry
- include units in IDs when the parameter is dimensional (`*_seconds`, `*_m`, `*_pct`)
- split mechanical enablement flags from numeric magnitudes (`*_enabled` as boolean capability/flag, not overloaded with scalar meaning)

Normalization examples:
- choose one cardinality suffix per namespace (`count` **or** `quantity`, not both)
- keep cooldown/duration fields in the mechanic-parameter registry rather than canonical target stats
- keep composite ownership centralized (`wall_*` derived targets resolved in central resolver, not redefined in evaluators)

These guardrails are intended to prevent canonical drift and evaluator-local reinterpretation while V2 registries are being authored.

## 11. Migration rules

### 11.1 V1 isolation
V1 code may be read, compared, or adapted from.
It is not a naming or ownership authority.

### 11.2 Adapter-only reuse
Existing V1 compilers/loaders may be reused only as temporary input adapters or comparison surfaces, not as the semantic core of V2.

### 11.3 Quarantine
Unknown or not-yet-mapped legacy identifiers may enter only through explicit quarantine mechanisms.
Quarantine must:
- be opt-in
- be logged
- be enumerable
- never silently pass as canonical

## 12. Implementation phases

### Phase A: master-spec and registries
Deliver:
- this master spec
- machine-readable registries
- file ownership map
- acceptance criteria

### Phase B: source normalization
Deliver normalized source-state adapters for all approved static systems.

### Phase C: contributor emission
Deliver canonical contributor-row emission for all static systems, all stats at once.

### Phase D: static resolution
Deliver central static resolver and composite/dependent static resolution.

### Phase E: parity and audit
Deliver diff surfaces comparing V1, ledger references, and V2 outputs.

### Phase F: runtime overlays
Deliver wave/perk/combat/boss overlay layers.

### Phase G: evaluator migration
Move consumers one by one onto V2 stable interfaces.

## 13. Acceptance criteria

A V2 implementation is not accepted unless all are true:

1. all required naming domains are explicit
2. all required static stages exist, including `baseline_gem_respec`
3. all static systems emit real contributor rows
4. no canonical contributor row uses fabricated placeholder IDs
5. all static target stats resolve through one horizontal resolver path
6. composite ownership is central and explicit
7. canonical names flow inward; legacy names are edge-adapted only
8. runtime fields are rejected from static resolution
9. unknown identifiers fail closed or enter explicit quarantine
10. parity/audit outputs are available for validation

## 14. Non-goals

This spec does not authorize:
- evaluator-specific shortcut rebuilds
- survival/econ/max-wave local ownership of static semantics
- silent carryover of V1 helper names into canonical V2 domains
- ad hoc contributor creation outside registries
- implementation-first reinterpretation of naming

## 15. Initial file ownership map

Recommended V2 ownership surfaces:

- `docs/v2/TOWERSIM_V2_MASTER_SPEC.md`
  - authoritative architecture and migration contract

- `tower_sim/v2/registry/canonical_target_stats.*`
  - canonical target stat registry

- `tower_sim/v2/registry/mechanic_parameters.*`
  - runtime mechanic parameter registry

- `tower_sim/v2/registry/environment_parameters.*`
  - environment/tier/tournament parameter registry

- `tower_sim/v2/registry/capabilities.*`
  - capability/feature-flag registry

- `tower_sim/v2/registry/contributors.*`
  - canonical contributor registry

- `tower_sim/v2/registry/aliases.*`
  - legacy -> canonical mappings only

- `tower_sim/v2/registry/stages.*`
  - stage applicability rules

- `tower_sim/v2/registry/dependencies.*`
  - composite/dependency graph

- `tower_sim/v2/adapters/*`
  - source-state normalization adapters

- `tower_sim/v2/emission/*`
  - contributor-row emitters

- `tower_sim/v2/resolution/*`
  - static target and derived resolution

- `tower_sim/v2/runtime/*`
  - runtime overlays only

- `tower_sim/v2/evaluators/*`
  - V2 evaluator consumers only

## 16. Immediate implementation instruction

No further V2 implementation should proceed until this spec is committed and the initial registries are generated from it.

Current provisional V2 scaffold files must be treated as non-authoritative until reconciled against this spec.

## 17. Canonical registry object model and rollout best practices

When substantial mechanics coverage already exists in repository sources, first freeze object classes, then populate only what current evaluators/mechanics actually consume.

### 17.1 Required object classes (do not merge)
1. **Canonical target stat**: stable evaluator-facing resolved values.
   - examples: `tower_hp`, `tower_regen`, `tower_damage`, `wall_hp`, `wall_regen`
2. **Runtime mechanic parameter**: direct knobs consumed by mechanic logic.
   - examples: `uw.black_hole.duration_seconds`, `guardian.attack.cooldown_seconds`
3. **Environment parameter**: run/tier/tournament context modifiers.
   - examples: `bc.enemy_attack_speed_pct`, `tier.enemy_hp_multiplier`
4. **Capability**: boolean/enum mechanic enablement or branch control.
   - examples: `capability.wall.enabled`, `capability.black_hole.enabled`
5. **Contributor**: provenance row from a source family mapped to exactly one destination object.
   - examples: `workshop.*`, `lab.*`, `card.*`, `module.*`, `perk.*`, `uw_upgrade.*`, `bot_upgrade.*`, `guardian_upgrade.*`

Fail-closed rule:
- if a value cannot be classified into one object class unambiguously, stop or quarantine explicitly.

### 17.2 State-plane separation
Do not mix these planes:
- **account/loadout state** (workshop levels, labs, equipped cards/modules, UW investments, chip levels)
- **environment state** (tier modifiers, BCs, tournament modifiers)
- **run state** (current HP/wall HP, cooldown timers, active effect state, wave-local dynamics)

Static registries must not absorb run-state fields.

### 17.3 Inclusion and promotion policy
Inclusion test for canonical registries:
- include only if resolver/runtime/evaluator consumes it as an independent semantic input today
- exclude if it is only a source/UI label, unlock naming surface, or transient helper field

Promotion rule:
- lab/card/module concepts remain contributors by default
- promote to mechanic/environment/capability registry only when they introduce a direct consumed runtime parameter

### 17.4 Collision and synonym control
Before adding a new ID:
1. detect semantic duplicates (`count` vs `quantity`)
2. converge source aliases to one canonical (`tower_hp` vs `tower_health`)
3. map alternates through aliases only
4. reject parallel canonicals for the same semantic concept

### 17.5 Registry-first implementation order
1. Freeze object-model registries (`v2_canonical_target_stats`, `v2_mechanic_parameters`, `v2_environment_parameters`, `v2_capabilities`).
2. Define `v2_contributor_ids` mapping each contributor to exactly one destination object and operation.
3. Add `v2_composite_dependencies` for central derived/composite ownership.
4. Enforce static/runtime boundaries through `v2_runtime_field_registry` deny-list checks.
5. Migrate adapters/emitters/evaluators only after registry validation gates pass.

### 17.6 Deterministic merge gates
Required gates per scoped migration:
- Gate A: no duplicate semantics within or across object-class registries
- Gate B: no unresolved alias leakage into canonical core
- Gate C: composite ownership remains central (no evaluator-local redefinition)
- Gate D: unknown identifiers fail closed or explicit quarantine only
- Gate E: parity/audit outputs emitted for changed domains

### 17.7 Naming contract split
Use two naming layers intentionally:
- provenance-rich contributor IDs (source-oriented)
- concise stable engine IDs for targets/mechanics/environment/capabilities

Do not force one grammar to serve both roles.

This workflow keeps the simulator deterministic and auditable while avoiding an overgrown single-registry model.


## 18. Kickoff playbook: how to start implementation

Use this sequence to begin execution without reopening architecture debates.

### 18.1 Week-1 goal (minimum deliverable)
Deliver a first machine-readable registry cut that covers currently-consumed v1 combat/survivability surfaces only.

Scope lock:
- include only IDs consumed by existing resolver/runtime/evaluator paths
- defer unmapped systems to explicit quarantine entries
- do not expand scope to "all wiki stats" in the first pass

### 18.2 Step-by-step startup sequence
1. **Inventory current consumers**
   - enumerate IDs read by evaluator/runtime/composite-resolution entrypoints
   - classify each ID into one object class: target stat, mechanic parameter, environment parameter, capability, contributor
2. **Freeze minimal object-model registries**
   - create initial lists for `v2_canonical_target_stats`, `v2_mechanic_parameters`, `v2_environment_parameters`, `v2_capabilities`
   - mark each item with provenance source and owner layer
3. **Define contributor mapping slice**
   - map only in-scope contributor families to destination object IDs and operations
   - enforce one contributor -> one destination semantic mapping
4. **Run collision/alias pass**
   - collapse duplicates (`count` vs `quantity`, `hp` vs `health`) through aliases
   - reject unresolved synonym conflicts until explicit decision is recorded
5. **Wire central dependency/composite rules**
   - encode `wall_*` and other composite ownership in central dependency registry only
   - verify no evaluator-local recomputation remains for scoped targets
6. **Enable fail-closed checks**
   - unknown IDs must fail or enter quarantine explicitly
   - no silent fallback to legacy names
7. **Publish parity snapshot**
   - produce a scoped parity report between existing outputs and registry-driven outputs for in-scope IDs

### 18.3 Definition of done for first migration slice
A first slice is complete only if all hold:
- all in-scope consumed IDs are classified into one object class
- all canonical IDs are duplicate-free after alias normalization
- all in-scope contributors map through registry definitions
- composite ownership for scoped targets is centralized
- unresolved identifiers are quarantined or rejected explicitly
- parity/audit output exists and is attached to the migration PR

### 18.4 Recommended PR slicing pattern
Keep PRs narrow and deterministic:
1. PR-1: object-model registry skeleton + naming/alias decisions
2. PR-2: first in-scope contributor mappings + operations
3. PR-3: composite/dependency wiring + fail-closed guards
4. PR-4: parity/audit evidence and evaluator cutover for scoped IDs

Do not combine all layers in one migration PR.


## 19. Plain-language version (no software jargon)

If the detailed sections feel too technical, use this practical version.

### 19.1 What we are doing
We are organizing game values into 4 simple buckets so we stop mixing different kinds of things:

1. **Core tower results** (the main values evaluators read)
   - examples: tower health, tower damage, wall health
2. **Mechanic settings** (values specific systems use while running)
   - examples: Black Hole duration, Golden Tower cooldown
3. **Environment settings** (wave/tier/BC context)
   - examples: enemy health multiplier, boss speed multiplier
4. **On/off flags** (feature enabled yes/no)
   - examples: poison swamp stun enabled

### 19.2 What a contributor row means
A contributor row is just: "this source value changes that destination value".

It must clearly say which bucket it points to (core result, mechanic setting, environment setting, or on/off flag).

### 19.3 How to work through this (simple order)
1. Start with values the simulator already uses today.
2. Put each one into exactly one bucket.
3. Make sure no value appears in two buckets.
4. Make sure old names point to one chosen name.
5. If a value is unclear, block it or quarantine it (do not guess).
6. Run parity checks and confirm outputs still match for in-scope areas.

### 19.4 What "done" means for a migration slice
A slice is done when:
- every in-scope value has one bucket,
- no duplicates remain,
- no silent fallback names remain,
- blocked/unknown items are explicit,
- parity output is attached to the PR.

### 19.5 Immediate next three steps
- **Step 1:** review edge IDs and fix any wrong bucket assignments.
- **Step 2:** expose a simple status report (counts per bucket + blocked items).
- **Step 3:** migrate downstream consumers off the old single-list assumption.

### 19.6 Current status
- Step 1 status: in progress (edge-ID review started; selected ultimate-mechanic IDs moved into mechanic settings).
- Step 2 status: complete (`summarize_v2_registry_status` reports counts plus blocked-item totals and `scripts/v2_registry_status.py` exposes it for users).
- Step 3 status: complete in static contract loading/tests (no required dependency on legacy single-list target registry for object-universe validation).
