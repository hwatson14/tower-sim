# Audit Surface Contracts

This document defines C13 audit-surface contract behavior.

## Surface classes (C13 scope)

- **full**: canonical/full-state surfaces intended to represent complete truth for their declared scope.
- **partial**: selected-context or policy-filtered surfaces that must not be interpreted as completeness artifacts.

## Current contract mapping

- `out/account_state.json` -> `full` (`canonical_full_state`)
- `out/state_matrix.json` -> `full` (`state_mode_resolution_matrix`)
- `out/diagnostics.json` -> `partial` (`selected_context`)
- `out/statbook_publishable.json` -> `partial` (`publishable_filtered`)
- `out/ep_oracle_compare.json` -> `partial` (`compare_context`)

## Completeness visibility requirement

At least one canonical audit artifact must expose explicit preset-lane presence including empty lanes.

This requirement is satisfied by `out/audit_surface_manifest.json` via:
- `preset_lane_completeness.<preset>.cards_explicit/cards_empty`
- `preset_lane_completeness.<preset>.modules_explicit/modules_empty`
- `preset_lane_completeness.<preset>.perks_explicit/perks_empty`

## Non-goals

- Artifact class taxonomy/provenance redesign (C14 scope).
- CI completeness gate design (C16 scope).
