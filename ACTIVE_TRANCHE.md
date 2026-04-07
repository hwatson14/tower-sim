# ACTIVE_TRANCHE.md

## Role

This file is a root governance source of truth for the active repository state.

It identifies:
- the current hardening sequence
- the exact active tranche
- what is already verified
- what must happen next
- stop conditions and closeout criteria

Governance truth for this repository lives directly in:
- this `ACTIVE_TRANCHE.md` file
- `BURNDOWN.yaml`

Machine-readable state lives in:
- `BURNDOWN.yaml`

---

## Current state

The repo is **not in broad rebuild territory**.
The repo has completed the prior hardening closeout sequence and the maintenance stabilization / hygiene tranche; freeze-candidate work must now certify that exact governed baseline rather than widen scope.

### Durable truths on the current baseline

- ownership layering remains intact (`app -> advisors -> evaluators -> simulators -> qe -> input`)
- runtime formula authority table is present and canonical coverage remains explicit
- native family query path is present for progression/timing/report surfaces
- the current active snapshot has a durable full-suite recertification artifact
- the latest full suite on the actual current worktree passed on **2026-04-07** (`342 passed`)
- formula surface policy remains active
- the repo's maintenance-mode claim is currently ahead of the actual hygiene/governance state

### Remaining constraints

- keep governance text synchronized with executable validation status and burndown state
- do not expand scope into broad refactor, new hardening seams, or formula-authority retirement in this tranche
- no app-side stat calculation
- no compare-only assumptions used to make dashboard values appear correct
- no `line_verification` or `input_dashboard` authority for displayed stats
- no stale `out/` trust
- no fallback routing as final architecture
- fail closed when the artifact contract is ambiguous rather than guessing

---

## Hardening sequence

| # | Name | Status |
|---|------|--------|
| T0 | Governance truth | COMPLETE |
| T1 | Streamlit contract execution | COMPLETE |
| T2 | QE authority closure | COMPLETE |
| T3 | Evaluator cleanup | COMPLETE |
| T4 | Thinning and polish | COMPLETE |

## Active tranche record: maintenance stabilization / hygiene - COMPLETE

### Goal

Turn the current green snapshot into a genuinely governed maintenance baseline.

This tranche is about:
1. explicit artifact-contract governance
2. worktree hygiene
3. test/inspector/publication alignment with the sanctioned artifact split
4. governance synchronization to the cleaned baseline

This tranche is not about:
1. Hardening G
2. another hardening seam
3. formula-authority retirement
4. new subsystem mechanics
5. app/UI polish
6. broad refactors

### Snapshot facts being stabilized

1. the actual current worktree is freshly full-suite green
2. Hardening E/F closures appear to hold operationally
3. formula surface policy remains active
4. the maintenance-mode claim is ahead of the actual hygiene state
5. the committed `out/` artifact contract is still implicit and must be made explicit

### Active verification items

1. COMPLETE: define the committed bounded `out/` contract
2. COMPLETE: distinguish the temp/full pipeline artifact contract from the committed bounded contract
3. COMPLETE: define policy for ad hoc `out_*` directories
4. COMPLETE: reduce tranche-owned residue to a maintenance-clean state
5. COMPLETE: refresh governance after cleanup so maintenance-mode wording is honest

### Exit criteria

Maintenance stabilization is complete only when all of the following are true:

- the sanctioned committed `out/` subset is explicit in active governance docs/index
- the temp/full pipeline artifact universe is explicitly separate
- tests/inspector/publication align with that split and fail closed on the wrong contract
- ad hoc `out_*` directories are removed or otherwise explicitly governed
- governance files reflect the cleaned baseline rather than the transitional closeout state
- `BURNDOWN.yaml` task statuses match this file

### Verification baseline

- `python app/run_stats.py --perk-mode max_progression_policy --out out`
- `python -m pytest -q`
- high-signal targeted tests around pipeline/publication/inspector and touched contract tests
- fresh inspection of:
  - `out/run_stats_query_rows_start_of_run.json`
  - `out/run_stats_query_rows_max_progression.json`
  - `out/run_stats_query_plan_start_of_run.json`
  - `out/run_stats_query_plan_max_progression.json`
  - `out/diagnostics.json`
  - `out/account_state.json`
  - `git status --short`

### Verification record

- targeted tranche-alignment suite passed on **2026-04-07** (`102 passed`)
- refreshed full suite passed on **2026-04-07** (`347 passed`) in **45.29s**
- refreshed `out/` inspection confirmed:
  - query-row artifacts remain bounded by state mode
  - query-plan artifacts remain bounded by state mode
  - `diagnostics.json` now publishes the explicit bounded run_stats output contract
  - committed `run_stats.json` excludes volatile timing telemetry; rebuild-stable review content remains separated from local diagnostics timing data
  - `account_state.json` refreshed through the sanctioned `run_stats` path
- ad hoc tracked output directories were removed and moved under ignore policy
- unrelated user-owned local edits outside this tranche were intentionally left untouched rather than folded into hygiene work

---

## Decision freeze (still active)

1. **Boss Waves remains interactive**, but only through a sanctioned app-level runtime facade
2. **Streamlit remains optional/import-safe**
3. **Legacy start/max statbooks are permanently removed**, not restored
4. **Formula surface policy remains active for compare/publication semantics after bridge-residue retirement**
5. **Repo should not be described as fully re-certified green** without a durable full-suite artifact for the current snapshot

---

## Stop conditions

Stop and report rather than improvising if any of the following occur:

- governance files disagree on active tranche or hardening order
- defining the committed `out/` contract exposes a deeper unresolved governance conflict
- cleaning the worktree would require bundling unrelated mechanic/code changes
- maintenance-mode cannot be made honest without another implementation tranche
- proposed changes force broad refactors instead of tranche-scoped stabilization
- maintenance work attempts to remove the active formula surface policy registry

---

## What not to do next

Do **not** start with:

- Hardening G
- another hardening seam
- formula-authority retirement
- new subsystem mechanics
- app/UI polish
- broad cleanup outside artifact governance and hygiene alignment

Those are sequencing mistakes at the current repo stage.
