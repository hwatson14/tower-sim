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
`PH4-A — Canonical migration ledger and denominator freeze`

## Authoritative plan section
`AI_EXECUTION_PLAN.md -> Phase 4 — Full stat-resolution migration to Query Engine -> PH4-A — Canonical migration ledger and denominator freeze`

## Objective
Freeze the exact Phase 4 migration denominator before any code migration begins so the repo has one explicit ledger for canonical stat-resolution scope, residual buckets, parity denominator, and benchmark denominator.

## Allowed local residue in this file
- active-slice clarification that does not modify tranche contract truth
- bounded blocker notes discovered while executing the active tranche
- denominator-freeze findings that must stay visible while PH4-A is active
- immediate stop conditions triggered by live repo truth

## Current tranche-local notes
- Phase 3 closeout remains complete in repo truth and is the prerequisite that promoted the repo into Phase 4.
- PH4-A is a control-and-ledger tranche first; it must freeze the migration denominator before any Phase 4 code migration or parity execution starts.
- The denominator freeze must classify every named family or stat group into canonical scope, compatibility-only scope, legacy merge-reference residue, or explicit out-of-phase scope.

## Legacy-surface rule after Phase 4
If `engine/stat_engine.py` and/or `engine/stat_resolution_core.py` remain after Phase 4, they remain only as:
- thin compatibility entrypoints, and/or
- non-canonical legacy merge/reference aids for reconciling work built from older baselines.

They must not:
- be named canonical owners of stat-resolution truth
- receive new canonical stat logic
- become routing destinations for new stat surfaces entering scope

## Immediate stop conditions
- Stop if a canonical stat group cannot name a Query Engine target owner.
- Stop if a surface cannot be assigned to either canonical Phase 4 scope or an explicit residual bucket.
- Stop if denominator scope changes after implementation begins without updating `AI_EXECUTION_PLAN.md`, `BURNDOWN.yaml`, and `ACTIVE_TRANCHE.md` first.
- Stop if execution would add new canonical stat logic to `engine/stat_engine.py` or `engine/stat_resolution_core.py`.
