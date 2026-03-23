# ACTIVE_TRANCHE.md

## Role

This file is the live execution cursor.

It identifies:
- the exact active tranche
- the exact plan section Codex should execute
- tranche-local residue and stop conditions only

It is not a second plan.
Canonical tranche-contract truth lives in `AI_EXECUTION_PLAN.md`.
Machine state lives in `BURNDOWN.yaml`.
Do not duplicate tranche contract text here. If contract truth changes, update `AI_EXECUTION_PLAN.md` first and then update this file only to point at the revised truth.

## Active phase
`PH4 — Full stat-resolution migration to Query Engine`

## Active tranche
`PH4-B — Declared family cutover to Query Engine`

## Authoritative plan section
`AI_EXECUTION_PLAN.md -> Phase 4 — Full stat-resolution migration to Query Engine -> PH4-B — Declared family cutover to Query Engine`

## Objective
Advance only the declared-family cutover tranche for Phase 4 once the PH4-A denominator freeze is closed in control truth, while keeping PH4-B explicitly blocked until the repo can move beyond one-family-only live delegation and the timing-family naming mismatch is resolved.

## Allowed local residue in this file
- active-slice clarification that does not modify tranche contract truth
- bounded blocker notes discovered at the PH4-B entry boundary
- cutover-entry facts that must stay visible while PH4-B is active
- immediate stop conditions triggered by live repo truth

## Current tranche-local notes
- Phase 3 closeout remains complete in repo truth and is the prerequisite that promoted the repo into Phase 4.
- `PH4A_CANONICAL_MIGRATION_LEDGER.md` is merged and keeps the PH4-A denominator freeze explicit enough for tranche promotion.
- `PH4A_FAMILY_ENTRY_MATRIX.md` is merged and remains the bounded PH4-B entry artifact for current code and test truth.
- PH4-A is complete as a control-and-ledger tranche, but that closeout does not imply PH4-B implementation has started.
- PH4-B is limited to declared family cutover only; it must not expand scope into undeclared families or non-family stat-group migration.
- Current code still delegates only `timing_tournament_no_perks`; all other declared families still fall back through legacy resolution.
- The timing-family blocker remains explicit: `state::cards.wave_accelerator.spawn_rate_acceleration` does not yet line up cleanly with `runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration`.
- PH4-B remains blocked in practice until the repo can truthfully move beyond one-family-only live delegation and the timing naming mismatch is resolved without treating the mismatch as implied cutover progress.

## Legacy-surface rule after Phase 4
If `engine/stat_engine.py` and/or `engine/stat_resolution_core.py` remain after Phase 4, they remain only as:
- thin compatibility entrypoints, and/or
- non-canonical legacy merge/reference aids for reconciling work built from older baselines.

They must not:
- be named canonical owners of stat-resolution truth
- receive new canonical stat logic
- become routing destinations for new stat surfaces entering scope

## Immediate stop conditions
- Stop if PH4-B work would imply declared family cutover has started before the current blocked entry conditions are cleared.
- Stop if any declared family other than `timing_tournament_no_perks` is described as live-delegated without corresponding code and test truth.
- Stop if the timing-family naming mismatch remains unresolved but is treated as if it were normal routed coverage.
- Stop if PH4-B work expands into non-family stat-group migration or undeclared family scope.
- Stop if execution would add new canonical stat logic to `engine/stat_engine.py` or `engine/stat_resolution_core.py`.
