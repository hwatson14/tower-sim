# IDS Tranche Contracts

This file expands the execution control register into Codex-ready tranche contracts.

## Contract schema

For each tranche:
- objective
- in scope
- out of scope
- hard dependencies
- required decisions
- exact files/artifacts expected
- acceptance tests
- stop conditions
- merge gate

---

## TRANCHE_IDS_C1_CONTRACT_REGISTRY

**Objective**  
Create a single canonical registry for preset names and section/schema ownership.

**In scope**
- canonical preset registry
- section layout registry
- consumer import points
- removal of local truth tables in executable code where practical, or explicit deprecation markers

**Out of scope**
- full runtime refactor
- output artifact redesign
- optimizer/provenance work

**Hard dependencies**  
None

**Required decisions**
- canonical preset names are fixed to:
  - Tourney
  - Farming
  - Milestone
  - Preset 4
  - Preset 5
- whether raw source aliases (`Preset 3`, `Testing`, placeholders) are normalized or rejected at each boundary

**Resolved decisions for current execution**
- normalize raw aliases only at ingestion boundaries:
  - `Preset 3` -> `Milestone`
  - `Testing` -> `Milestone`
  - `Placeholder 4th preset` -> `Preset 4`
  - `Placeholder 5th preset` -> `Preset 5`
- after ingestion, non-canonical names are invalid
- canonical artifacts, tests, fixtures, and runtime inputs must use canonical names only

**Expected artifacts**
- `registry/preset_contract.yaml`
- `registry/section_layout_contract.yaml`
- optional `registry/preset_aliases.yaml`
- `tests/test_preset_contract_registry.py`

**Acceptance tests**
- all executable consumers import or derive from canonical preset contract
- no executable file owns an independent preset truth table without explicit suppression note
- section layout truth is not duplicated across active parser/UI paths

**Stop condition**
- contract artifacts exist and the key active consumers are switched over
- duplicate active truth tables are either removed or explicitly retired

**Merge gate**
- human review required

---

## TRANCHE_IDS_C5_STATE_SEMANTICS

**Objective**  
Define and implement explicit semantics for missing, empty, invalid, zero, and synthetic state.

**In scope**
- state binding rules
- identity semantics
- missing/empty serialization rules
- fallback removal or explicit tagging

**Out of scope**
- UI redesign
- compare policy redesign unless required for semantics

**Hard dependencies**
- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`

**Required decisions**
- exact semantics matrix for:
  - missing
  - empty
  - invalid
  - zero
  - synthetic/transient
- whether any fail-open behaviors remain allowed

**Resolved decisions for current execution**
- `missing` = absent required preset/lane/field -> invalid in canonical flows, fail closed
- `empty` = explicitly present but empty -> valid and explicit
- `zero` = valid numeric zero, distinct from missing/empty
- `invalid` = unrecognized name/shape/value -> fail closed
- `synthetic` = transient non-canonical runtime/compare state -> explicitly typed/quarantined, never serialized as canonical preset state
- no fail-open behavior in canonical flows
- no silent fallback to default preset, `Farming`, empty list, or zero

**Expected artifacts**
- `docs/state_semantics.md`
- `tests/test_state_semantics.py`
- fixture demonstrating missing != empty != zero
- identity test proving distinct hashes/states where required

**Acceptance tests**
- invalid preset names fail closed
- missing preset-family state is not silently rebound
- empty presets/slots are explicitly representable

**Stop condition**
- semantics documented and encoded in tests
- key binding/identity helpers updated

**Merge gate**
- human review required

---

## TRANCHE_IDS_C2_RUNTIME_FIVE_PRESET

**Objective**  
Make runtime/progression/engine accept and handle all five canonical presets.

**In scope**
- progression state mode mapping
- runtime request validation
- scenario/runtime preset acceptance
- runtime acceptance matrix

**Out of scope**
- compare synthetic namespace cleanup
- fixture refresh

**Hard dependencies**
- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`
- `TRANCHE_IDS_C5_STATE_SEMANTICS`

**Expected artifacts**
- expanded progression/runtime tests for all five presets
- runtime acceptance matrix artifact
- removal of 3-preset-only hard rejections

**Acceptance tests**
- `Preset 4` and `Preset 5` are valid runtime/progression inputs
- no runtime path throws because a canonical preset is “unsupported”

**Stop condition**
- engine-level five-preset support proven by tests/artifact

**Merge gate**
- human review required

---

## TRANCHE_IDS_C11_PERK_PRESET_CONTRACT

**Objective**  
Bring perks onto the canonical preset contract or explicitly isolate allowed transient types.

**In scope**
- perk config parse/bind rules
- active perk preset normalization
- removal of hidden `default` pseudo-preset
- elimination of multi-key preset merge behavior for canonical flows

**Out of scope**
- perk balance/math changes
- timeline optimization

**Hard dependencies**
- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`
- `TRANCHE_IDS_C5_STATE_SEMANTICS`

**Required decisions**
- whether any transient generated perk sets may exist, and if so, how they are typed and isolated

**Expected artifacts**
- `tests/test_perk_preset_contract.py`
- updated perk parser/binder
- explicit policy doc or contract note for transient perk-set classes

**Acceptance tests**
- one canonical active perk preset selected for canonical flows
- no implicit merge of requested + active + default preset keys
- no hidden sixth preset namespace in canonical path

**Stop condition**
- perk preset resolution is deterministic and canonically typed

**Merge gate**
- human review required

---

## TRANCHE_IDS_C12_NAMESPACE_HYGIENE

**Objective**  
Quarantine synthetic namespaces so they never appear in canonical artifacts or identity unless explicitly typed as transient.

**In scope**
- compare-state naming hygiene
- projected-max and timeline synthetic namespace handling
- serialization boundaries
- artifact writer filters/tagging

**Out of scope**
- compare scoring policy
- UI cosmetics

**Hard dependencies**
- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`
- `TRANCHE_IDS_C5_STATE_SEMANTICS`
- `TRANCHE_IDS_C11_PERK_PRESET_CONTRACT`

**Expected artifacts**
- `docs/namespace_hygiene.md`
- `tests/test_namespace_hygiene.py`
- regenerated canonical artifacts with no synthetic preset names
- explicit transient artifact path if needed

**Acceptance tests**
- canonical/publishable artifacts contain only canonical preset names
- synthetic compare/runtime namespaces are typed as transient and isolated
- state identity does not fingerprint synthetic namespaces as canonical preset identity

**Stop condition**
- no synthetic names leak into canonical artifact families

**Merge gate**
- human review required

---

## TRANCHE_IDS_C10_CLEAN_SECTION_INGESTION

**Objective**  
Make Relics/Vault compiler ingestion fact-only and remove downstream blacklist cleanup dependence.

**In scope**
- compiler parsers for Relics and Vault
- removal of polluted rows from compiled state
- QE/export cleanup through upstream correctness

**Out of scope**
- UI display headers for those sections

**Hard dependencies**
- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`

**Expected artifacts**
- `tests/test_relics_vault_fact_ingestion.py`

**Acceptance tests**
- compiled Relics/Vault contain only fact rows
- downstream blacklist cleanup can be removed or reduced substantially

**Stop condition**
- pollution is eliminated at compile stage

**Merge gate**
- PR review

---

## TRANCHE_IDS_C7_WSPLUS_TYPED_MODEL

**Objective**  
Replace WS+ ad hoc interpretation with a typed preset-aware model and QE routing.

**In scope**
- WS+ schema definition
- compiler typed model
- QE routing
- debug/export surface update

**Out of scope**
- unrelated preview styling

**Hard dependencies**
- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`
- `TRANCHE_IDS_C5_STATE_SEMANTICS`

**Required decisions**
- exact WS+ column semantics and extra field meaning

**Expected artifacts**
- WS+ schema/contract file
- `tests/test_wsplus_typed_model.py`
- QE artifact proving preset-sensitive routing
- debug/export artifact preserving structure

**Acceptance tests**
- no first-parseable-float heuristics remain
- selected preset affects WS+ rows correctly
- full WS+ structure is visible in canonical/debug artifacts

**Stop condition**
- WS+ is fully typed and routed

**Merge gate**
- human review required

---

## TRANCHE_IDS_C8_UW_TYPED_TRACKS

**Objective**  
Preserve UW track identity explicitly instead of reconstructing it positionally.

**In scope**
- compiler UW model
- export/QE track naming
- removal of special-case order repair

**Out of scope**
- non-UW compare policy

**Hard dependencies**
- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`

**Expected artifacts**
- `tests/test_uw_typed_tracks.py`

**Acceptance tests**
- each UW track has explicit attribute identity end-to-end
- no external order map needed to interpret compiled UW rows

**Stop condition**
- positional track semantics removed from canonical path

**Merge gate**
- PR review

---

## TRANCHE_IDS_C9_BOT_TYPED_STATE

**Objective**  
Make bot state explicit about raw level and resolved value/unit.

**In scope**
- compiler bot model
- export/preview bot representation

**Out of scope**
- bot progression balance

**Hard dependencies**
- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`

**Expected artifacts**
- `tests/test_bot_typed_state.py`

**Acceptance tests**
- bot rows carry both raw level and resolved value/unit where required
- export/debug semantics are explicit and consistent

**Stop condition**
- compiler/QE/export agree on bot meaning

**Merge gate**
- PR review

---

## TRANCHE_IDS_C13_AUDIT_SURFACE_CONTRACTS

**Objective**  
Declare which surfaces are full truth vs partial selected-context views, and make completeness explicit.

**In scope**
- debug/preview/query surface contracts
- canonical completeness artifact policy
- truncation labeling

**Out of scope**
- visual redesign beyond required labels/columns

**Hard dependencies**
- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`
- `TRANCHE_IDS_C5_STATE_SEMANTICS`

**Required decisions**
- what counts as canonical full-state artifact vs partial execution-context artifact

**Expected artifacts**
- `docs/audit_surface_contracts.md`
- `tests/test_audit_surface_contracts.py`
- one full completeness artifact per family or one global matrix

**Acceptance tests**
- partial views are labeled
- empty presets/slots are explicit in at least one canonical audit artifact
- previews do not masquerade as completeness artifacts

**Stop condition**
- audit surface classes are explicit and tested

**Merge gate**
- human review required

---

## TRANCHE_IDS_C14_ARTIFACT_OUTPUT_CONTRACTS

**Objective**  
Make output artifact classes explicit and preserve provenance/completeness semantics.

**In scope**
- run_stats output taxonomy
- optimizer/overlay provenance fields
- artifact class metadata
- output contract docs/tests

**Out of scope**
- underlying optimizer scoring logic

**Hard dependencies**
- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`
- `TRANCHE_IDS_C5_STATE_SEMANTICS`
- `TRANCHE_IDS_C12_NAMESPACE_HYGIENE`
- `TRANCHE_IDS_C13_AUDIT_SURFACE_CONTRACTS`

**Expected artifacts**
- `docs/artifact_contracts.md`
- `tests/test_artifact_contracts.py`
- regenerated artifacts with class/provenance metadata

**Acceptance tests**
- each artifact declares class: canonical / publishable / compare / selected-context / transient
- provenance includes enough preset/state context
- synthetic namespaces excluded from canonical/publishable classes

**Stop condition**
- artifact family contracts are explicit and enforced

**Merge gate**
- human review required

---

## TRANCHE_IDS_C15_VERIFICATION_REALIGNMENT

**Objective**  
Refresh tests, fixtures, helpers, and checked-in outputs so green verification matches the canonical contract.

**In scope**
- fixture refresh
- helper defaults
- removal of stale/synthetic expectations from canonical tests
- explicit five-preset completeness tests

**Out of scope**
- unrelated new feature coverage

**Hard dependencies**
- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`
- `TRANCHE_IDS_C2_RUNTIME_FIVE_PRESET`
- `TRANCHE_IDS_C5_STATE_SEMANTICS`
- `TRANCHE_IDS_C11_PERK_PRESET_CONTRACT`
- `TRANCHE_IDS_C12_NAMESPACE_HYGIENE`
- `TRANCHE_IDS_C13_AUDIT_SURFACE_CONTRACTS`
- `TRANCHE_IDS_C14_ARTIFACT_OUTPUT_CONTRACTS`

**Expected artifacts**
- refreshed fixtures
- `tests/test_five_preset_completeness.py`
- removal of stale `Testing` and placeholder expectations from canonical tests
- synthetic-state tests explicitly typed as transient-only

**Acceptance tests**
- canonical tests use only canonical five presets unless explicitly transient
- fixtures no longer contradict canonical preset naming
- non-Farming presets have direct coverage

**Stop condition**
- green tests actually mean canonical preset contract compliance

**Merge gate**
- human review required

---

## TRANCHE_IDS_C16_COMPLETENESS_MATRIX

**Objective**  
Create the global completeness proof artifact and CI gate.

**In scope**
- family completeness matrix
- per-family lane/slot completeness status
- CI assertion

**Out of scope**
- unrelated dashboards

**Hard dependencies**
- `TRANCHE_IDS_C1_CONTRACT_REGISTRY`
- `TRANCHE_IDS_C5_STATE_SEMANTICS`
- `TRANCHE_IDS_C13_AUDIT_SURFACE_CONTRACTS`
- `TRANCHE_IDS_C14_ARTIFACT_OUTPUT_CONTRACTS`

**Expected artifacts**
- `out/family_completeness_matrix.json`
- `tests/test_family_completeness_matrix.py`
- CI gate wiring

**Acceptance tests**
- one artifact/test can prove all five presets are explicitly represented for each family
- empty preset/slot semantics are visible and machine-checkable

**Stop condition**
- completeness can be asserted directly rather than inferred

**Merge gate**
- human review required
