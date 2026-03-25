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
`PH4-B — Declared family cutover to Query Engine` (blocked at entry gate; authority reset applied)

## Authoritative plan section
`AI_EXECUTION_PLAN.md -> Phase 4 — Full stat-resolution migration to Query Engine -> PH4-B — Declared family cutover to Query Engine`

## Objective
Advance the declared-family cutover tranche for Phase 4. The timing-family naming mismatch has been resolved and timing-family live delegation has been expanded. PH4-B now continues toward progression-family cutover.

## Allowed local residue in this file
- active-slice clarification that does not modify tranche contract truth
- bounded blocker notes discovered at the PH4-B entry boundary
- cutover-entry facts that must stay visible while PH4-B is active
- immediate stop conditions triggered by live repo truth

## Current tranche-local notes

### Authority reset (applied this tranche)
- Query Engine (bounded API: `stat_query_kernel.py`, `family_baseline_materializer.py`, `state_identity.py`) is the sole canonical execution path for new Phase 4 stat-resolution work. This is now encoded in `AI_EXECUTION_PLAN.md` governing truth and `ARCHITECTURE.md`.
- `engine/stat_resolution_core.py` is legacy/reference-only under Phase 4. No new canonical stat logic may be added. The "canonical stat-resolution owner" label it held before Phase 4 is vacated.
- `engine/stat_engine.py` is thin compatibility entrypoint only. Not a canonical implementation target.
- Handoff docs (`PH4A_CANONICAL_MIGRATION_LEDGER.md`, `PH4A_FAMILY_ENTRY_MATRIX.md`) are handoff artifacts, not canonical merged-control truth, unless explicitly promoted.

### Naming reset (applied this tranche)
- `state::` and `runtime_mechanic_param::` naming patterns are migration-era/legacy aliasing. They are not the canonical naming target for new Phase 4 work.
- New Phase 4 work must not silently expand old `state::` or `runtime_mechanic_param::` naming. Any backward-compatibility bridge must be declared in the alias contract explicitly.
- The live instance: `state::cards.wave_accelerator.spawn_rate_acceleration` vs `runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration` is an open PH4-B entry blocker, not implied coverage.

### PH4-A closeout status
- Phase 3 closeout remains complete in repo truth and is the prerequisite that promoted the repo into Phase 4.
- `PH4A_CANONICAL_MIGRATION_LEDGER.md` is merged and keeps the PH4-A denominator freeze explicit enough for tranche promotion.
- `PH4A_FAMILY_ENTRY_MATRIX.md` is merged and remains the bounded PH4-B entry artifact for current code and test truth.
- PH4-A is complete as a control-and-ledger tranche.
- **Timing-family naming mismatch resolved**: `state::cards.wave_accelerator.spawn_rate_acceleration` is now the canonical surface ID used throughout `engine/stat_engine.py`, `_DELEGATED_FAMILY_SURFACE_IDS`, and all KB contracts. The legacy `runtime_mechanic_param::cards.wave_accelerator.spawn_rate_acceleration` alias remains valid for input-row routing only (via `naming-contract-pack-v2-remap.csv`), not as a delegation surface ID.
- **Timing-family live delegation expanded**: `timing_tournament_no_perks` and `timing_farm_with_perks` are now live-delegated through the Query Engine compatibility entrypoint. Both are covered by tests in `tests/test_resolve_stats_delegation.py` and `tests/test_timing_query_migration.py`.
- **`scenario_rules` guard added**: `_infer_manifest_approved_family` now requires `source_family == 'scenario_rules'` rows to prevent non-timing inputs (e.g. progression rows with `preset_name='Farming'`) from being incorrectly delegated as a timing family.
- **`timing_scenario_probe` surface set declared, not yet live-delegated via compat shim**: it has no fixed preset-name convention distinct from `'Farming'`; it is accessible only via the direct QE path. Its entry into the compat shim requires a separate tranche slice.
- **`timing_family_context` helper added**: `tests/helpers.py` now exports `timing_family_context()` covering all three declared timing families; `test_r86_completion.py` parametrised test is no longer skipped.
- PH4-B next focus is progression-family cutover: `progression_start_of_run`, `progression_runtime_no_perks`, `progression_runtime_with_perks`.
- PH4-B remains limited to declared family cutover only; it must not expand scope into undeclared families or non-family stat-group migration.

## Legacy-surface rule after Phase 4
If `engine/stat_engine.py` and/or `engine/stat_resolution_core.py` remain after Phase 4, they remain only as:
- thin compatibility entrypoints, and/or
- non-canonical legacy merge/reference aids for reconciling work built from older baselines.

They must not:
- be named canonical owners of stat-resolution truth
- receive new canonical stat logic
- become routing destinations for new stat surfaces entering scope

## Immediate stop conditions
- Stop if PH4-B work expands into non-family stat-group migration or undeclared family scope.
- Stop if execution would add new canonical stat logic to `engine/stat_engine.py` or `engine/stat_resolution_core.py`.
- Stop if `timing_scenario_probe` is described as live-delegated via compat shim without a disambiguating preset name distinct from 'Farming'.
- Stop if progression-family delegation starts before progression-family test infrastructure is confirmed in place.
