# R86 pre-Codex freeze pack tightening

## Purpose
R86 tightens R85 so Codex implements the stat-query refactor as an extension of the repo's current control plane rather than a parallel contract stack.

## What changed from R85
1. Explicit layering over existing contracts:
   - `kb/global-rules/contracts/scenario-runtime-inputs.yaml`
   - `kb/global-rules/contracts/state-modes.yaml`
2. Frozen family-to-state-mode mapping.
3. Harmonised overlay vocabulary.
4. Frozen phase-1 baseline materialiser seam.
5. Added worked examples for baseline rows, overlay deltas, and query responses.
6. Fixed iteration naming to R86.

## Architectural position
Phase 1 implementation target remains:
- baseline-materialised canonical/support contributor maps
- bounded scenario families
- immutable overlay deltas
- on-demand composed-surface resolution
- initial workload families only: `timing_v1`, `progression_v1`

## Layering rules
The contract stack is now explicitly:
1. Existing repo contracts remain authoritative for low-level runtime/state semantics:
   - `scenario-runtime-inputs.yaml`
   - `state-modes.yaml`
2. New stat-query contracts extend that stack for bounded query/materialisation behavior.
3. Query-engine implementation may reference runtime inputs and state modes, but must not redefine them.

## Phase-1 non-goals remain unchanged
- no geometry migration
- no broad combat-helper migration
- no optimiser migration
- no unbounded scenario family growth
- no full resolved-statbook baseline emission
