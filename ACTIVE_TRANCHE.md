# ACTIVE_TRANCHE.md

## Role

This file is the live tranche cursor for the current **repo hardening phase**.

It identifies:
- the current hardening sequence
- the exact active tranche
- what is already verified
- what must happen next
- stop conditions and closeout criteria

Narrative contract truth lives in the root handoff pack:
- `towersim_hardening_handoff_pack_v5.zip` → `01_MASTER_HARDENING_PLAN.md`
- `towersim_hardening_handoff_pack_v5.zip` → `02_DECISION_LOG_AND_AMBIGUITIES.md`
- `towersim_hardening_handoff_pack_v5.zip` → `03_ACCEPTANCE_CHECKLIST.md`

Machine-readable state lives in:
- `BURNDOWN.yaml`

---

## Current state

The repo is **not in broad rebuild territory**.

The whitelist rebuild is largely complete.
The repo is now in **concentrated hardening territory**, where small remaining ownership and governance seams are higher risk than broad structural migrations.

### What is already materially true

- high-signal architecture/app suites are green on the reviewed baseline
- governance truth is now aligned to the hardening sequence
- Streamlit now contains an explicit contract freeze header
- Streamlit imports and artifact flows have moved toward app-owned seams
- runtime formula authority is explicitly bridge-tagged
- simulator/QE runtime hardening remains a repo strength

### What is still not true

- Streamlit contract execution is not fully complete yet (test strategy remains mixed)
- native QE execution is not fully separated from compat/report execution
- evaluators still import private QE/compiler helpers
- some Streamlit tests still entrench helper-local mixed-ownership behavior

---

## Hardening sequence

| # | Name | Status |
|---|------|--------|
| T0 | Governance truth | ✅ COMPLETE |
| T1 | Streamlit contract execution | ✅ COMPLETE |
| T2 | QE authority closure | ✅ COMPLETE |
| T3 | Evaluator cleanup | ✅ COMPLETE |
| T4 | Thinning and polish | ✅ COMPLETE |

---

## Active tranche: release hardening closeout — ✅ COMPLETE

### Goal

Finalize hardening closeout evidence and publish recertification artifacts.

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

### Required T4 work

1. ✅ thin `app/streamlit_inspector.py` while preserving boundary contracts
2. ✅ thin large QE/evaluator files only where ownership remains unambiguous
3. ✅ clean residue helpers/mapping duplication without behavior drift

### Exit criteria

Release closeout is complete only when all of the following are true:

- full acceptance checklist is executed and archived
- durable full-suite recertification artifact is captured
- `BURNDOWN.yaml` task statuses match this file

### Closeout verification artifact

- `pytest -q` executed on **2026-04-02 (UTC)** with result: **187 passed**.

### Verification

- targeted thinning-change tests plus high-signal regression checks
- consistency check against:
  - handoff pack `01_MASTER_HARDENING_PLAN.md`
  - handoff pack `02_DECISION_LOG_AND_AMBIGUITIES.md`
  - handoff pack `03_ACCEPTANCE_CHECKLIST.md`

---

## Decision freeze (still active)

1. **Boss Waves remains interactive**, but only through a sanctioned app-level runtime facade
2. **Streamlit remains optional/import-safe**
3. **Legacy start/max statbooks are permanently removed**, not restored
4. **Formula-authority bridge remains active** until explicit retirement conditions are met
5. **Streamlit helper-local tests must be rewritten toward boundary/contract tests**, not preserved as-is
6. **Repo should not be described as fully re-certified green** without a durable full-suite artifact for the current snapshot

---

## Next tranche: maintain-only

### Goal

Preserve invariants and prevent boundary regressions while the repo is in maintenance mode.

### Why next

Because T0-T4 tranche items are complete, release closeout can rely on converged governance and seam ownership.

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
