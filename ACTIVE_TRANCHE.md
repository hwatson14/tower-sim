# ACTIVE_TRANCHE

## Tranche ID
`TRANCHE_BOOTSTRAP_CONTROL_SYSTEM_V1`

## Objective
Bootstrap the repo-native AI execution control system so future Codex runs operate from:
- durable rules in `AGENTS.md`
- canonical whole-program truth in `AI_MIGRATION_EXECUTION_PLAN.md`
- one active tranche file
- machine-readable task/burndown state

## Scope in
- `AI_MIGRATION_EXECUTION_PLAN.md`
- `ACTIVE_TRANCHE.md`
- `BURNDOWN.yaml`

## Scope out
- runtime mechanic changes
- query-kernel delegation work
- `stat_input_compiler.py` seam code changes
- `run_stats.py` decomposition
- estimator / optimiser / advisor implementation

## Tasks included
- P0-T2 planning-control alignment for execution artifacts
- bootstrap `ACTIVE_TRANCHE.md`
- bootstrap `BURNDOWN.yaml`

## Acceptance criteria
- `ACTIVE_TRANCHE.md` exists and defines one active tranche only.
- `BURNDOWN.yaml` exists and tracks delivery + verification state separately.
- `AI_MIGRATION_EXECUTION_PLAN.md` names the control-system artifacts and their roles.

## Required verification
- review all newly added or updated control files for internal consistency
- ensure task IDs referenced by the tranche exist in `AI_MIGRATION_EXECUTION_PLAN.md`
- ensure `BURNDOWN.yaml` status fields match the tranche scope

## Blockers
- none

## Update rule
Only update this file when:
1. the current tranche is completed and verified, or
2. a blocker requires replacing it with a newly approved tranche.

## Stop conditions
Stop once the acceptance criteria above are satisfied and the burndown has been updated to reflect the new control-system state.
