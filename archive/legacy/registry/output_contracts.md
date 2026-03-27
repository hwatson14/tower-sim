# Output Contracts

This document defines the C13 audit-surface contract behavior and the C14 artifact-output contract layer and C15/C16 closeout expectations.

---

## Audit Surface Contracts (C13)

### Surface classes (C13 scope)

- **full**: canonical/full-state surfaces intended to represent complete truth for their declared scope.
- **partial**: selected-context or policy-filtered surfaces that must not be interpreted as completeness artifacts.

### Current contract mapping

- `out/account_state.json` -> `full` (`canonical_full_state`)
- `out/state_matrix.json` -> `full` (`state_mode_resolution_matrix`)
- `out/diagnostics.json` -> `partial` (`selected_context`)
- `out/statbook_publishable.json` -> `partial` (`publishable_filtered`)
- `out/ep_oracle_compare.json` -> `partial` (`compare_context`)

### Completeness visibility requirement

At least one canonical audit artifact must expose explicit preset-lane presence including empty lanes.

This requirement is satisfied by `out/audit_surface_manifest.json` via:
- `preset_lane_completeness.<preset>.cards_explicit/cards_empty`
- `preset_lane_completeness.<preset>.modules_explicit/modules_empty`
- `preset_lane_completeness.<preset>.perks_explicit/perks_empty`

### Non-goals

- Artifact class taxonomy/provenance redesign (C14 scope).
- CI completeness gate design (C16 scope).

---

## Artifact Contracts (C14)

### Goals

- Make artifact class explicit rather than implied by filename.
- Make provenance explicit rather than inferred from context.
- Keep canonical artifacts cleanly separated from selected-context and compare-only artifacts.
- Provide a deterministic completeness artifact that can be used as a gate.

### Artifact classes

- **canonical_snapshot**: a canonical state artifact intended to represent the current run/package truth for its declared scope.
- **derived_matrix**: a deterministic matrix derived from canonical state over a fixed policy space.
- **publishable_view**: a policy-filtered projection of canonical state.
- **compare_view**: an artifact whose purpose is comparison, audit, or diagnosis rather than canonical publication.
- **verification_view**: an artifact whose purpose is verification, closure, or residue tracking rather than canonical publication.
- **audit_manifest**: a manifest describing other artifacts or coverage state.

### Contract values

- **full**: intended to be complete for the artifact's declared scope.
- **partial**: intentionally selected-context, filtered, or otherwise not completeness-bearing.

### Provenance values

- **current_run_generated**: generated from the current package/run invocation.
- **policy_filtered_from_current_run**: generated from current run truth after publication policy is applied.
- **compare_generated_from_current_run_and_ep**: generated from current run truth plus EP comparison material.
- **verification_generated_from_current_run_and_compare**: generated from current run truth and comparison outputs.
- **manifest_generated_from_current_run**: manifest or completeness metadata generated from the current run.

### Required artifact mapping

| Surface | Artifact class | Contract | Provenance |
|---|---|---|---|
| `account_state.json` | canonical_snapshot | full | current_run_generated |
| `stat_inputs.json` | canonical_snapshot | full | current_run_generated |
| `statbook.json` | canonical_snapshot | full | current_run_generated |
| `state_matrix.json` | derived_matrix | full | current_run_generated |
| `statbook_publishable.json` | publishable_view | partial | policy_filtered_from_current_run |
| `diagnostics.json` | compare_view | partial | compare_generated_from_current_run_and_ep |
| `ep_oracle_compare.json` | compare_view | partial | compare_generated_from_current_run_and_ep |
| `line_by_line_verification.json` | verification_view | partial | verification_generated_from_current_run_and_compare |
| `survivor_closure_report.json` | verification_view | partial | verification_generated_from_current_run_and_compare |
| `audit_surface_manifest.json` | audit_manifest | full | manifest_generated_from_current_run |
| `artifact_contract_manifest.json` | audit_manifest | full | manifest_generated_from_current_run |
| `family_completeness_matrix.json` | audit_manifest | full | manifest_generated_from_current_run |

### Five-preset rule

Canonical preset-bearing artifacts must use exactly these presets:

- `Tourney`
- `Farming`
- `Milestone`
- `Preset 4`
- `Preset 5`

Synthetic or transient preset names must not appear in canonical artifacts.

### C15 verification realignment

The verification layer must assert:

- the five-preset contract is complete and explicit
- artifact provenance is explicit
- canonical artifacts do not carry synthetic preset namespaces
- family completeness is emitted in a deterministic machine-readable artifact

### C16 completeness matrix

`out/family_completeness_matrix.json` is the closeout proof artifact.

It must:

- enumerate the canonical five presets
- enumerate the key compiled families
- expose mapped vs unmapped counts by family
- expose whether preset lanes are explicit or empty for cards, modules, and perks
- be suitable for a test or CI gate that fails closed when canonical preset or family coverage regresses
