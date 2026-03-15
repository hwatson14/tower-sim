# v3 Bootstrap Plan

This folder is an isolated rebuild track for TowerSim v3.

## Seed artifact
- Source KB zip: `../tower_kb_frozen_regenerated.zip`
- Canonical knowledge source for v3 rebuild work: `tower_kb_frozen_regenerated.zip`
- Required KB source for v3 runtime work: extracted KB tree at `kb/` (single canonical working tree).

## Guardrails
- Do not seed v3 from alternate KB snapshots unless explicitly re-approved; `tower_kb_frozen_regenerated.zip` is canonical for this track.
- Keep active v2 runtime (`tower_sim/`) untouched unless explicitly requested.
- Build v3 as a separate codebase with its own composition root under `v3/`.
- Preserve deterministic, fail-closed behavior and explicit provenance for all mechanics.

## Initial next steps
1. Unpack the KB artifact into a bounded reference subtree in `v3/`.
2. Define a minimal v3 contract + repo map local to `v3/`.
3. Implement the smallest deterministic core first (`MAX_WAVE` parity target).
4. Add explicit verification fixtures before broader feature porting.
