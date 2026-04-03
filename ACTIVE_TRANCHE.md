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
The repo is in **concentrated hardening territory** with active blockers that require small, scoped closure PRs.

### Durable truths on the current baseline

- ownership layering remains intact (`app -> advisors -> evaluators -> simulators -> qe -> input`)
- runtime formula authority table is present and canonical coverage remains explicit
- native family query path is present for progression/timing/report surfaces

### Remaining constraints

- closeout governance text must stay synchronized with executable validation status and burndown state.
- do not expand scope into broad refactor or tranche reshaping while preserving closeout evidence.

---

## Hardening sequence

| # | Name | Status |
|---|------|--------|
| T0 | Governance truth | 🔄 IN PROGRESS |
| T1 | Streamlit contract execution | ✅ COMPLETE |
| T2 | QE authority closure | 🔄 IN PROGRESS |
| T3 | Evaluator cleanup | ✅ COMPLETE |
| T4 | Thinning and polish | 🔄 IN PROGRESS |

## Active tranche record: release hardening closeout — 🔄 IN PROGRESS

### Goal

Finalize hardening closeout evidence and publish recertification artifacts after blocker closure.

### T1 closeout status

T1 is now complete:
1. ✅ resolved the legacy statbook contradiction
2. ✅ removed private QE imports from Streamlit
3. ✅ removed direct KB/manual file reads from Streamlit
4. ✅ moved Boss Waves runtime orchestration behind a sanctioned app-level seam
5. ✅ rewrote Streamlit tests away from helper-local private assertions toward app boundary/contract coverage

### T2 closeout status

1. ✅ remove `qe.kernel` module-level dependency on `qe.stat_resolution.resolve_bucket_value`
2. ✅ remove `qe.routing` reliance on compat delta execution for manifest-approved native delta operation
3. ✅ keep formula-authority bridge explicit with a recorded/tested retirement threshold

### T3 closeout status

1. ✅ replaced underscore-prefixed evaluator compiler imports with public surfaces
2. ✅ added regression coverage preventing evaluator private-import reintroduction

### Required closure work

1. preserve workshop authority contract alignment (approved-exception policy/data alignment)
2. preserve native report routing diagnostics in statbooks/snapshots
3. preserve report-fallback callsite boundary discipline in `qe/routing.py`
4. preserve exact max-rend formula parity on progression/run-stats path
5. keep recertification artifacts current as implementation changes land

### Exit criteria

Release closeout is complete only when all of the following are true:

- full acceptance checklist is executed and archived
- durable full-suite recertification artifact is captured
- `BURNDOWN.yaml` task statuses match this file

### Closeout verification artifact

- full-suite recertification artifact recorded for the active snapshot via `pytest -q`.
- latest full-suite validation attempt on **2026-04-03** passed (`275 passed`).
- CI fast-lane invariant: `.github/workflows/ci.yml` enforces `pytest -q` wall-clock budget at **10 seconds** on `ubuntu-latest`; over-budget runs fail closed and publish `pytest-durations` artifact (`pytest-durations.log`).

### Verification

- targeted thinning-change tests plus high-signal regression checks
- consistency check against:
  - `ACTIVE_TRANCHE.md`
  - `BURNDOWN.yaml`

---

## Decision freeze (still active)

1. **Boss Waves remains interactive**, but only through a sanctioned app-level runtime facade
2. **Streamlit remains optional/import-safe**
3. **Legacy start/max statbooks are permanently removed**, not restored
4. **Formula-authority bridge retirement remains explicitly tracked in `BURNDOWN.yaml` thresholds**
5. **Repo should not be described as fully re-certified green** without a durable full-suite artifact for the current snapshot

---

## Next tranche: maintain-only

### Goal

Preserve invariants and prevent boundary regressions while the repo is in maintenance mode.

### Why next

Because several closeout blockers remain open, release closeout must stay in targeted hardening mode until those blockers are resolved and recertified.

---

## Stop conditions

Stop and report rather than improvising if any of the following occur:

- governance files disagree on active tranche or hardening order
- proposed changes force broad refactors instead of tranche-scoped hardening
- implementing T4 closure requires architecture reshaping instead of scoped residue reduction
- release closeout is claimed without durable acceptance-checklist evidence

---

## What not to do next

Do **not** start with:

- file splitting
- general cleanup
- Input-tab polish in isolation
- preserving helper-local Streamlit tests as the primary strategy
- declaring the repo finished because high-signal suites look healthy

Those are sequencing mistakes at the current repo stage.
