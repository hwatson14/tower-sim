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
The repo has completed **release hardening closeout** for the current snapshot and should stay in **maintenance-mode / targeted regression prevention** unless a new scoped blocker appears.

### Durable truths on the current baseline

- ownership layering remains intact (`app -> advisors -> evaluators -> simulators -> qe -> input`)
- runtime formula authority table is present and canonical coverage remains explicit
- native family query path is present for progression/timing/report surfaces
- the current active snapshot has a durable full-suite recertification artifact

### Remaining constraints

- closeout governance text must stay synchronized with executable validation status and burndown state
- do not expand scope into broad refactor or tranche reshaping while preserving closeout evidence
- formula-authority bridge publish-block residue has been retired; formula surface policy remains the active compare/publication policy registry

---

## Hardening sequence

| # | Name | Status |
|---|------|--------|
| T0 | Governance truth | COMPLETE |
| T1 | Streamlit contract execution | COMPLETE |
| T2 | QE authority closure | COMPLETE |
| T3 | Evaluator cleanup | COMPLETE |
| T4 | Thinning and polish | COMPLETE |

## Active tranche record: release hardening closeout - COMPLETE

### Goal

Finalize hardening closeout evidence and publish recertification artifacts after blocker closure.

### T1 closeout status

T1 is now complete:
1. resolved the legacy statbook contradiction
2. removed private QE imports from Streamlit
3. removed direct KB/manual file reads from Streamlit
4. moved Boss Waves runtime orchestration behind a sanctioned app-level seam
5. rewrote Streamlit tests away from helper-local private assertions toward app boundary/contract coverage

### T2 closeout status

1. remove `qe.kernel` module-level dependency on `qe.stat_resolution.resolve_bucket_value`
2. remove `qe.routing` reliance on compat delta execution for manifest-approved native delta operation
3. retire obsolete formula-authority bridge publish-block residue while preserving active formula surface policy ownership

### T3 closeout status

1. replaced underscore-prefixed evaluator compiler imports with public surfaces
2. added regression coverage preventing evaluator private-import reintroduction

### Closeout verification status

1. COMPLETE: workshop authority contract alignment preserved under approved-exception policy/data checks
2. COMPLETE: native report routing diagnostics preserved in statbooks/snapshots
3. COMPLETE: report-fallback callsite boundary discipline preserved in `qe/routing.py`
4. COMPLETE: exact max-rend formula parity preserved on progression/run-stats path
5. COMPLETE: recertification artifacts refreshed for the current validated snapshot

### Exit criteria

Release closeout is complete only when all of the following are true:

- full acceptance checklist is executed and recorded
- durable full-suite recertification artifact is captured
- `BURNDOWN.yaml` task statuses match this file

### Closeout verification artifact

- full-suite recertification artifact recorded for the active snapshot via `pytest -q`
- latest full-suite validation attempt on **2026-04-07** passed (`342 passed`)
- reassessment rerun on **2026-04-07** measured `pytest -q` at **43.29s** on current HEAD versus **79.63s** on pre-optimization baseline `b8f30ce`
- CI fast-lane invariant: `.github/workflows/ci.yml` enforces `pytest -q` wall-clock budget at **10 seconds** on `ubuntu-latest`; over-budget runs fail closed and publish `pytest-durations` artifact (`pytest-durations.log`)

### Verification

- targeted thinning-change tests plus high-signal regression checks
- full `pytest -q`
- consistency check against:
  - `ACTIVE_TRANCHE.md`
  - `BURNDOWN.yaml`

---

## Decision freeze (still active)

1. **Boss Waves remains interactive**, but only through a sanctioned app-level runtime facade
2. **Streamlit remains optional/import-safe**
3. **Legacy start/max statbooks are permanently removed**, not restored
4. **Formula surface policy remains active for compare/publication semantics after bridge-residue retirement**
5. **Repo should not be described as fully re-certified green** without a durable full-suite artifact for the current snapshot

---

## Next tranche: maintain-only

### Goal

Preserve invariants and prevent boundary regressions while the repo is in maintenance mode.

### Why next

Because release hardening closeout is complete for the current snapshot, subsequent work should remain maintenance-mode and invariant-preserving unless a new scoped blocker appears.

---

## Stop conditions

Stop and report rather than improvising if any of the following occur:

- governance files disagree on active tranche or hardening order
- proposed changes force broad refactors instead of tranche-scoped hardening
- maintenance work attempts to remove the active formula surface policy registry rather than only retiring dead bridge residue
- release closeout is claimed without durable acceptance-checklist evidence

---

## What not to do next

Do **not** start with:

- file splitting
- general cleanup
- Input-tab polish in isolation
- preserving helper-local Streamlit tests as the primary strategy
- declaring the repo finished without a fresh full-suite artifact on the current snapshot

Those are sequencing mistakes at the current repo stage.
