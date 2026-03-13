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

1. `v2_target_stats`
2. `v2_contributor_ids`
3. `v2_alias_map`
4. `v2_source_state_schema`
5. `v2_stage_applicability`
6. `v2_contributor_operations`
7. `v2_composite_dependencies`
8. `v2_runtime_field_registry`
9. `v2_quarantine_registry` for explicitly tolerated migration exceptions

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

- `tower_sim/v2/registry/target_stats.*`
  - canonical target stat registry

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
