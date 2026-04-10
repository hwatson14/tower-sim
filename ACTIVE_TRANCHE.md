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
The repo has completed the prior hardening closeout sequence and the maintenance stabilization / hygiene tranche.
The active program is now the v49 Streamlit-first product scope reset:
- make every current-scope canonical, user-relevant stat visible in Streamlit
- keep those visible stats KB/QE-aligned, provenance-bearing, and contract-governed
- deliver the sanctioned max-wave simulator through the Streamlit product surface
- meet the current-stage performance contract honestly
- remove stale duplicate authority and residue where they undermine truth, speed, or blind maintainability

### Durable truths on the current baseline

- ownership layering remains intact (`app -> advisors -> evaluators -> simulators -> qe -> input`)
- runtime formula authority table is present and canonical coverage remains explicit
- native family query path is present for progression/timing/report surfaces
- the current active snapshot has a durable full-suite recertification artifact
- the latest full suite on the actual current worktree passed on **2026-04-07** (`349 passed`)
- formula surface policy remains active
- the repo already exposes a live Boss Waves Streamlit surface wired through the sanctioned app/simulator path
- committed QE query-row artifacts already include `state::economy.interest_per_wave_pct`, `state::wall.rebuild_seconds`, and `state::tower.thorns_damage_pct`

### Remaining constraints

- keep governance text synchronized with executable validation status and burndown state
- treat `TowerSim_bible_v49.md` as the sole active product-and-scope authority for the current program
- do not widen into evaluator or optimiser delivery
- no app-side stat calculation
- no compare-only assumptions used to make dashboard values appear correct
- no `line_verification` or `input_dashboard` authority for displayed stats
- no stale `out/` trust
- no fallback routing as final architecture
- no second active authority path
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

## Active tranche record: v49 Streamlit-first canonical stat and simulator program - IN PROGRESS

### Goal

Turn the governed maintenance baseline into the current scoped product:
- canonical visible stat truth in Streamlit
- sanctioned max-wave simulator delivery through Streamlit
- honest performance evidence for the active product path
- residue and governance cleanup that reduces authority blur

This tranche is about:
1. truth protection and scope reset
2. visible-stat contract activation
3. canonical stat visibility completion
4. Streamlit operational product completion
5. sanctioned max-wave simulator completion
6. targeted performance hardening
7. residue cleanup and governance synchronization

This tranche is not about:
1. evaluator delivery
2. optimiser delivery
3. speculative CI or precompute programs
4. UI-local truth patches
5. broad rewrite for aesthetic cleanup
6. broad refactors outside touched owner surfaces

### Snapshot facts being advanced

1. the actual current worktree has a recent durable full-suite green baseline from **2026-04-07**
2. the repo already has a live Boss Waves tab and sanctioned app/simulator runtime seam
3. current committed QE surfaces already cover `Interest / Wave`, `Wall Rebuild`, and the current `tower thorns` naming
4. root governance still misstates the active program as maintenance stabilization
5. the remaining open completion gate is honest current-stage performance evidence for the sanctioned product paths

### Active verification items

1. COMPLETE: sync root governance to the v49 program and active authority order
2. COMPLETE: prove the visible-stat contract is active in implementation and tests
3. COMPLETE: current-scope canonical stat visibility is now published through Streamlit via the sanctioned owner chain, including QE-owned bots, guardians, modules, and ultimate-weapon sections
4. COMPLETE: the sanctioned max-wave simulator product contract is now visible in Streamlit with stable payload summary, explicit runtime controls, downloadable row output, and simulator-backed execution diagnostics
5. IN PROGRESS: run honest current-stage performance verification and sanctioned-path hardening
6. TODO: demote or remove stale duplicate authority and residue after parity

### Current blockers inside the active program

1. The v49 interactive performance target is still open, so P5 remains the active blocker to full program completion.

### Exit criteria

The v49 current-stage program is complete only when all of the following are true:

- every current-scope canonical user-relevant stat has a visible home in Streamlit
- each visible row follows the sanctioned row contract and authority chain
- missingness and non-recon behavior are explicit rather than silently backfilled
- Streamlit can operate the sanctioned max-wave simulator path with explicit runtime controls
- current-scope simulator tests and touched contract tests pass
- performance claims for the active product path are evidenced honestly
- stale root governance no longer misstates the active program
- `BURNDOWN.yaml` task statuses match this file

### Verification baseline

- `python -m app.run_stats`
- `pytest -q tests/app/test_input_dashboard_contract.py`
- `pytest -q tests/app/test_stats_dashboard_contract.py`
- `pytest -q tests/simulators/test_run_executor.py`
- targeted pytest selection for touched owner surfaces
- broader `pytest -q` when a phase claims closure
- fresh inspection of:
  - `out/run_stats_query_rows_start_of_run.json`
  - `out/run_stats_query_rows_max_progression.json`
  - `out/stats_dashboard.json`
  - `out/input_dashboard.json`
  - `out/diagnostics.json`
  - `git status --short`

### Current performance evidence

- benchmark baseline command: `python -m app.run_stats`
- repo snapshot: `d04f328`
- machine note: Windows 10 Pro, x64, Intel i7-6700K, 16 GB RAM
- pre-hardening measured wall-clock runs on **2026-04-10**:
  - run 1: **4548.26 ms**
  - run 2: **4132.39 ms**
  - run 3: **4300.90 ms**
- post-hardening measured wall-clock runs on **2026-04-10**:
  - run 1: **3934.13 ms**
  - run 2: **3695.59 ms**
  - run 3: **3912.26 ms**
- post-import-thinning measured wall-clock runs on **2026-04-10**:
  - run 1: **1663.64 ms**
  - run 2: **1758.34 ms**
  - run 3: **1890.40 ms**
- post-surface-id-caching measured wall-clock runs on **2026-04-10**:
  - run 1: **1390.17 ms**
  - run 2: **1446.00 ms**
  - run 3: **1391.22 ms**
- post-bound-input-reuse measured wall-clock runs on **2026-04-10**:
  - run 1: **1135.47 ms**
  - run 2: **1205.17 ms**
  - run 3: **1217.87 ms**
- post-dashboard-artifact measured wall-clock runs on **2026-04-10**:
  - run 1: **1580.19 ms**
  - run 2: **1644.26 ms**
  - run 3: **1477.16 ms**
- post-loader-and-registry-hardening measured wall-clock runs on **2026-04-10**:
  - run 1: **1938.07 ms**
  - run 2: **1563.81 ms**
  - run 3: **1449.09 ms**
- post-loader-and-registry-hardening repeated in-process session runs on **2026-04-10**:
  - run 1: **790.63 ms**
  - run 2: **568.52 ms**
  - run 3: **547.86 ms**
- post-shared-yaml-cache-and-compiler-hardening measured wall-clock runs on **2026-04-10**:
  - run 1: **1421.29 ms**
  - run 2: **1785.38 ms**
  - run 3: **1354.65 ms**
- post-shared-yaml-cache-and-compiler-hardening repeated in-process session runs on **2026-04-10**:
  - run 1: **704.59 ms**
  - run 2: **487.24 ms**
  - run 3: **544.84 ms**
- sanctioned Boss Waves payload benchmark (`build_boss_wave_payload`, Tier 14, wave 500, boss step 10, `stop_on_failure=false`) on **2026-04-10** after the explicit payload contract landed:
  - run 1: **2655.53 ms**
  - run 2: **1763.50 ms**
  - run 3: **1799.30 ms**
- sanctioned Boss Waves payload benchmark (`build_boss_wave_payload`, Tier 14, wave 500, boss step 10, `stop_on_failure=false`) on **2026-04-10** after the workshop-mutation trigger closure:
  - run 1: **2913.87 ms**
  - run 2: **2166.65 ms**
  - run 3: **2006.79 ms**
- sanctioned Boss Waves payload benchmark (`build_boss_wave_payload`, Tier 14, wave 500, boss step 10, `stop_on_failure=true`) on **2026-04-10** with the new interactive default:
  - run 1: **570.16 ms**
  - run 2: **95.76 ms**
  - run 3: **101.10 ms**
- interpretation: sanctioned-path YAML/contract loading, import-thinning, surface-id caching, bound-input reuse, input-loader hardening, default dependency-registry reuse, shared YAML contract caching, and compiler cold-path hardening improved the `run_stats` hot path materially. The bounded contract still writes dashboard artifacts, and the true fresh CLI path remains well above the preserved v49 target band even though repeated in-process session runs are materially faster. Boss Waves is now product-complete with stable payload summary, explicit execution diagnostics, and no delta fallback on the live path; its default `stop_on_failure=true` mode is directionally interactive on warm runs. The remaining blocker is still `run_stats`-path performance, whose measured cost is now concentrated in residual cold YAML/contract work and `compile_stat_inputs` startup cost rather than the earlier boss-wave delta-fallback bug.

### Verification record

- targeted tranche-alignment suite passed on **2026-04-07** (`104 passed`)
- refreshed full suite passed on **2026-04-07** (`349 passed`) in **44.85s**
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
- code and current artifacts disagree materially about a current-scope visible or simulator surface
- a requested change would require UI-local truth invention or a second active authority path
- performance claims would rely on hidden benchmark shortcuts
- evaluator or optimiser work starts to creep back into scope
- proposed changes force broad refactors instead of tranche-scoped progress

---

## What not to do next

Do **not** start with:

- evaluator delivery
- optimiser delivery
- UI-local truth patches
- speculative precompute or CI work
- broad rewrite for aesthetic cleanup
- broad cleanup outside the active owner/path surfaces

Those are sequencing mistakes at the current repo stage.
