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
- replace the Boss Waves row-engine target with a staged Table 1 / Table 2 / combat kernel while preserving the current product surface until cutover is explicitly in scope
- meet the current-stage performance contract honestly
- remove stale duplicate authority and residue where they undermine truth, speed, or blind maintainability

### Durable truths on the current baseline

- ownership layering remains intact (`app -> advisors -> evaluators -> simulators -> qe -> input`)
- runtime formula authority table is present and canonical coverage remains explicit
- native family query path is present for progression/timing/report surfaces
- the current active snapshot has a durable full-suite recertification artifact
- the latest historical shipped-baseline audit from `tower-sim-src(9).zip` on **2026-04-15** was **not** fully green (`392 passed, 1 failed, 1 skipped`) until rebuilt-state repair work ran
- the latest rebuilt-worktree full suite on the repaired current baseline passed on **2026-04-15** (`399 passed`)
- formula surface policy remains active
- the repo already exposes a live Boss Waves Streamlit surface wired through the legacy sanctioned app/simulator path; current structural replacement work must not treat that row-engine as the target architecture
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
5. sanctioned max-wave simulator completion and staged Boss Waves replacement build
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

1. the repaired current worktree has a durable full-suite green baseline from **2026-04-15**
2. the repo already has a live Boss Waves tab and sanctioned app/simulator runtime seam
3. current committed QE surfaces already cover `Interest / Wave`, `Wall Rebuild`, and the current `tower thorns` naming
4. root governance still misstates the active program as maintenance stabilization
5. after the 2026-04-15 final product-correctness hardening tranche, the remaining open completion gate is honest current-stage performance evidence for the sanctioned product paths

### Active verification items

1. COMPLETE: sync root governance to the v49 program and active authority order
2. COMPLETE: prove the visible-stat contract is active in implementation and tests
3. COMPLETE: recover the Stats product contract so canonical visibility is operator-useful in Streamlit rather than a resolved-section-heavy dump
4. COMPLETE: recover Streamlit operational product usability so Boss Waves remains usable even when optional Stats/debug data is partial or absent
5. COMPLETE: wire Boss Waves perk evolution through the sanctioned simulator path and revalidate the no-delta-fallback live path
6. COMPLETE: clean the active repo-root control allowlist and remove stale zip-pack residue
7. COMPLETE: recertify the repaired Streamlit product contract with targeted tests, full pytest, `app.run_stats`, and a UI-level Streamlit harness run
8. COMPLETE: recertify the Boss Waves product surface so the main table is operator-facing, the raw row dump is demoted to debug, and the active DR/contact assumptions used by the solver are visible in the product surface
9. COMPLETE: repair fresh-clone Stats contract truth, live preset/view-state wiring, grouped Modules layout, cumulative Bot/Guardian spend, mojibake normalization, and primary-surface reconciliation semantics
10. COMPLETE: repair Boss Waves semantics so the product uses one canonical run-context contract, separates actual boss cadence from checkpoint sampling, and fails closed for Tourney when required tournament-wave context is unavailable
11. COMPLETE: remove the hidden fresh-clone generated-artifact dependency from the touched Stats contract test family
12. COMPLETE: harden the visible product so UW supplemental/UW+ handling, Bot/Guardian cumulative spend and totals, Guardian Scout truth, per-surface recon semantics, and Boss Waves regen auditability are all visible and defensible in the live product surface
13. COMPLETE: build and harden the Boss Waves staged replacement architecture: compiled RunPlan, explicit Table 1/Table 2 registries, Table 1 survivability contributor bundles, Table 2 scenario transforms, v21 event-only combat, avg/min/max lanes, and operator-table handles, without depending on the legacy row-engine hot path
14. COMPLETE: run bounded parity/shadow validation between the sanctioned live Boss Waves path and the staged replacement path; result was **parity sufficient for cutover planning**, with no production replacement-path fixes required during parity
15. COMPLETE: define the Boss Waves cutover plan, including split cutover phases, required field-map artifact, acceptance gates, operational rollback, and temporary legacy disposition
16. COMPLETE: implement Phase 2A Boss Waves cutover for operator table and summary only, with an actual product-consumption-derived field map, centralized `app.pipeline` source-selection/rollback seam, replacement-backed operator rows, legacy-compatible download rows, legacy-compatible diagnostics, and app-level tests
17. NEXT: define Phase 2B only after Phase 2A stabilizes; Phase 2B is limited to CSV/export and diagnostics source switching and must preserve rollback/shadow support

### Current blockers inside the active program

1. Boss Waves Phase 2A is implemented for operator table and summary only; this is not approval for Phase 2B, legacy removal, or broader app/product work.
2. CSV/export and diagnostics remain on the legacy-compatible Boss Waves payload split until a separate Phase 2B tranche maps and verifies them.
3. The repaired Stats contract must remain workshop-led: no reintroduction of Canonical Overview as a primary panel and no resolved-section-heavy default workflow.
4. Delta fallback remains guarded by live-path tests and is not a sanctioned default; do not weaken that gate while resuming performance work.

### Boss Waves cutover plan

This plan is governance for staged Boss Waves cutover. Phase 2A is now implemented for operator table and summary only. It does not authorize Phase 2B, legacy removal, UI-local truth, or compatibility shims.

#### Cutover scope map

| Seam / component | Current live source | Future replacement source | Cutover rule |
|---|---|---|---|
| Operator table source | `app.pipeline.build_boss_wave_payload(...)` consuming `simulators.run_executor.build_boss_wave_table_payload(...)` rows | staged Table 2 rows from `simulators.evaluator_kernel.build_scenario_overlay_table(...)`, rendered through operator-row handles | switch in Phase 2A only after the field map proves all table fields are equivalent, transformed, or explicitly absent |
| Summary source | legacy payload `summary` from `build_boss_wave_table_payload(...)` | replacement summary derived from explicit `avg` summary lane and replacement overlay rows | switch with operator table in Phase 2A |
| CSV/export source | legacy product rows and product formatting | replacement operator rows plus field-map-governed export columns | switch later in Phase 2B after 2A stabilizes |
| Diagnostics source | legacy payload `diagnostics` including legacy runtime owners, delta counts, and continuous-DPS model markers | replacement diagnostics covering RunPlan identity, Table 1/Table 2 registry ids, v21 TTK model, lane policy, parity status, and rollback state | switch later in Phase 2B after 2A stabilizes |
| Fixture/testing ownership | legacy `tests/simulators/test_run_executor.py`, app pipeline contract tests, staged `tests/simulators/test_evaluator_kernel.py`, and shadow parity tests | staged-kernel tests plus explicit app-level cutover tests and parity/shadow regression tests | maintain both until legacy demotion/removal is separately approved |
| Legacy comparison / shadow mode | bounded read-only shadow validation against sanctioned live seam | future shadow mode should compare product-facing fields through the field map, not invent a second engine | keep during 2A/2B stabilization |
| Rollback switch / fallback path | legacy Boss Waves product path remains available | app-level Boss Waves source selection can return to legacy | must be operational and tested before any product source switch |

#### Required Boss Waves field map artifact

Before any actual cutover tranche, create a field map that lists every product-facing Boss Waves field and explicitly records:

- legacy field/source
- replacement field/source
- status: equivalent, transformed, intentional semantic difference, not directly comparable, or not exposed
- product surface: table, summary, export, diagnostics
- normalization/tolerance policy for comparable fields
- owner of the transformation, if transformed
- rollback impact if the field is missing or malformed

The field map must cover at minimum: `display_wave`, effective attack wave, effective health wave, enemy attack, enemy health, final wall HP, final wall regen, boss TTK, survival margin, survives/fail state, first failed wave, max surviving wave, lane policy, and all fields currently used by CSV/export and diagnostics.

#### Phased cutover sequence

1. **Phase 0 - Planning freeze**
   - Current planning state only.
   - No product switch.
   - No legacy removal.
   - Record semantic differences, rollback plan, and required field map.

2. **Phase 1 - Shadow-ready cutover definition**
   - Keep the live product on the legacy path.
   - Produce the required Boss Waves field map artifact.
   - Keep the bounded parity matrix green.
   - Define the app-level source-selection and rollback seam without switching default behavior.

3. **Phase 2A - Operator table and summary source switch**
   - Switch only the visible operator table and summary source to the staged replacement path.
   - Keep CSV/export and diagnostics sourced from the existing legacy-compatible product contract unless explicitly mapped as pass-through.
   - Keep the legacy path available as rollback/shadow.
   - Do not remove legacy code.

4. **Phase 2B - CSV/export and diagnostics source switch**
   - Begin only after Phase 2A stabilizes.
   - Switch CSV/export fields through the field map.
   - Switch diagnostics to replacement-owned diagnostics while preserving enough legacy/shadow diagnostics to support rollback decisions.

5. **Phase 3 - Stabilization and monitoring**
   - Run replacement primary and legacy shadow where feasible.
   - Keep parity matrix and app-level product tests green.
   - Track intentional semantic differences, especially v21 event-only TTK versus legacy continuous-DPS proxy behavior.

6. **Phase 4 - Legacy demotion/removal planning**
   - Only after 2A/2B/3 prove stable.
   - Decide whether legacy becomes reference-only or is removed in a separate legacy-disposition tranche.
   - Removal requires proof that no active consumer needs legacy row-engine outputs.

#### Acceptance gates by phase

| Phase | Required gates |
|---|---|
| Phase 0 | cutover scope map documented; split 2A/2B phases documented; no app cutover; no legacy removal; semantic differences and blockers listed |
| Phase 1 | field map exists and covers table/summary/export/diagnostics; parity matrix remains green; `pytest -q` passes; no replacement bugs in divergence ledger; rollback seam design reviewed; non-comparable fields explicitly handled |
| Phase 2A | operator table source uses replacement; summary source uses replacement; CSV/export and diagnostics are not switched except mapped pass-through; app-level tests prove table/summary use replacement; parity matrix remains green; rollback action verified; `pytest -q` passes; v21 TTK and `avg/min/max` lane policy preserved |
| Phase 2B | export field map implemented; diagnostics field map implemented; app-level export/diagnostics tests pass; diagnostics expose active source and rollback state; parity matrix remains green; `pytest -q` passes |
| Phase 3 | replacement primary and legacy shadow remain comparable for mapped fields; no unresolved replacement bugs; rollback criteria exercised or dry-run verified; intentional semantic differences remain visible |
| Phase 4 | no active consumer depends on legacy Boss Waves row-engine outputs; governance and tests identify legacy as removable/reference-only; removal/demotion tests pass; `pytest -q` passes |

#### Operational rollback strategy

- **Rollback owner:** the Boss Waves app/pipeline cutover owner for the future cutover tranche. Until that tranche exists, rollback ownership remains unassigned and cutover must not start.
- **Rollback seam:** the future app-level Boss Waves source-selection seam for `build_boss_wave_payload(...)` product sourcing.
- **Rollback action:** set Boss Waves product sourcing back to the legacy sanctioned path (`app.pipeline.build_boss_wave_payload(...)` -> `simulators.run_executor.build_boss_wave_table_payload(...)`) and disable replacement primary sourcing while leaving shadow logging available if safe.
- **Rollback verification:** rerun the app-level Boss Waves contract tests, the parity/shadow test, and full `pytest -q`; verify the product table and summary again come from the legacy path and diagnostics identify the rollback state.
- **Rollback triggers:**
  - missing, malformed, or unmapped visible operator-table field
  - summary max surviving wave / first failed wave mismatch outside the accepted semantic-difference policy
  - replacement emits fail-closed ambiguity for normal supported product inputs
  - parity/shadow matrix classifies any mismatch as replacement bug
  - app-level Boss Waves table/summary/export/diagnostics tests fail
  - diagnostics cannot identify active source, model semantics, or rollback state
  - v21 event-only TTK, lane order `avg/min/max`, or summary lane `avg` regresses

#### Legacy disposition plan

- Legacy Boss Waves runtime code stays temporarily through Phase 2A, Phase 2B, and Phase 3.
- During early cutover, legacy is rollback and shadow/reference support, not the target architecture.
- Legacy comparison support may remain until all product-facing fields are mapped and stable.
- Legacy demotion/removal is a separate Phase 4 tranche and requires:
  - green parity/shadow evidence after replacement primary sourcing
  - green app-level product tests for table, summary, export, and diagnostics
  - proof that no active consumer depends on legacy row-engine-only outputs
  - governance sync that no longer describes legacy as the active product source

#### Remaining blockers before Phase 2B / broader cutover

1. CSV/export field mapping is not yet proven against replacement-owned export rows; Phase 2A keeps `download_rows` legacy-compatible.
2. Diagnostics field mapping is not yet proven for replacement RunPlan/Table 1/Table 2/v21 model metadata; Phase 2A keeps diagnostics legacy-compatible.
3. Phase 2B needs app-level tests proving export and diagnostics source switching while preserving rollback.
4. Intentional semantic differences, especially v21 event-only TTK versus legacy continuous-DPS proxy logic, must be visible in Phase 2B diagnostics.
5. Legacy removal remains blocked until table, summary, export, diagnostics, parity/shadow support, and rollback evidence are all green after stabilization.
6. Phase 2B still requires a fresh full-suite run and parity/shadow confirmation on the cutover branch.

### Exit criteria

The v49 current-stage program is complete only when all of the following are true:

- every current-scope canonical user-relevant stat has a visible home in Streamlit
- each visible row follows the sanctioned row contract and authority chain
- missingness and non-recon behavior are explicit rather than silently backfilled
- Streamlit can operate the sanctioned max-wave simulator path with explicit runtime controls
- current-scope simulator tests and touched contract tests pass
- Boss Waves staged kernel exists as compiled RunPlan plus Table 1 common trajectory and Table 2 scenario overlay/v21 combat outputs, with explicit registries, derived wall HP/regen from staged contributors, avg/min/max lanes, explicit avg summary-lane policy, operator-table handles, and no hot-path dependency on the legacy row-engine
- Boss Waves Phase 2A has switched operator table/summary only through a field-map-backed, rollback-tested `app.pipeline` seam; CSV/export and diagnostics remain Phase 2B
- performance claims for the active product path are evidenced honestly
- stale root governance no longer misstates the active program
- `BURNDOWN.yaml` task statuses match this file

### Verification baseline

- `python -m app.run_stats`
- `pytest -q tests/app/test_input_dashboard_contract.py`
- `pytest -q tests/app/test_stats_dashboard_contract.py`
- `pytest -q tests/app/test_pipeline_functional.py`
- `pytest -q tests/app/test_pipeline_ui_contracts.py`
- `pytest -q tests/simulators/test_run_executor.py`
- targeted pytest selection for touched owner surfaces
- broader `pytest -q` when a phase claims closure
- UI-level Streamlit harness verification of the repaired Stats/Boss Waves surface
- distinguish shipped-baseline truth from rebuilt-worktree truth when they differ
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
- post-write-path-contract-normalization measured wall-clock runs on **2026-04-10**:
  - run 1: **1011.11 ms**
  - run 2: **1045.87 ms**
  - run 3: **934.96 ms**
- rebuilt-worktree verification after the 2026-04-15 final product-correctness hardening tranche:
  - `python -m pytest -q` -> **399 passed**
  - `python -m pytest -q tests/app/test_pipeline_functional.py tests/simulators/test_run_executor.py tests/app/test_stats_dashboard_contract.py tests/shared/test_import_boundaries.py tests/app/test_pipeline_ui_contracts.py` -> **165 passed**
  - `python -m app.run_stats` -> **passed**
- live product acceptance verification after the 2026-04-15 final product-correctness hardening tranche:
  - Streamlit harness preset switching -> **passed**
  - primary Stats surfaces remain Workshop / Ultimate Weapons / Bots / Guardians / Modules -> **passed**
  - Boss Waves surface exposes cadence and regen auditability in the visible operator contract -> **passed**
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
- interpretation: sanctioned-path YAML/contract loading, import-thinning, surface-id caching, bound-input reuse, input-loader hardening, default dependency-registry reuse, shared YAML contract caching, compiler cold-path hardening, and bounded write-path contract normalization improved the `run_stats` hot path materially. The bounded contract still writes dashboard artifacts, and the true fresh CLI path has now moved to roughly **0.93s-1.05s**, but it remains well above the preserved v49 target band even though repeated in-process session runs are materially faster. Boss Waves is now product-complete on the repaired worktree baseline with stable payload summary, explicit execution diagnostics, canonical resolved run context, actual boss cadence separated from checkpoint sampling, and no delta fallback on the live path; Tourney now fails closed instead of silently inventing missing tournament-wave context. The remaining blocker is still `run_stats`-path performance, whose measured cost is now concentrated in residual cold YAML/contract work and `compile_stat_inputs` startup cost rather than the earlier boss-wave cadence/context defects.

### Verification record

- targeted tranche-alignment suites passed on **2026-04-14** across Stats contract, pipeline functional, simulator, UI contract, and import-boundary coverage
- visual/semantic acceptance recovery passed on **2026-04-14** for the live primary Stats/Boss Waves surface:
  - preset switching updates the visible product state without a rebuild
  - primary Stats tables now follow the shared display grammar (`—`, max 2 decimals, normalized units, no mojibake)
  - Bots now use start-of-run-only primary semantics with truthful cumulative medal spend and no misleading effective-range column
  - Guardians now use truthful cumulative-bit and start-state semantics with simple green recon where base equals start state
  - workshop `Cap` wiring now includes ceiling/floor truth for `Defense %`, `Shockwave Interval`, and `Wall Rebuild`
  - full `pytest -q` passed on the repaired baseline (`397 passed`)
- refreshed full suite passed on **2026-04-07** (`349 passed`) in **44.85s**
- corrective recovery tranche targeted suites passed on **2026-04-12**, including:
  - `tests/app/test_stats_dashboard_contract.py`
  - `tests/app/test_pipeline_functional.py`
  - `tests/app/test_pipeline_ui_contracts.py`
  - `tests/qe/test_generic_perk_multiplier_resolution.py`
  - `tests/qe/test_routing_checkpoint_consumer_bundle.py`
  - `tests/simulators/test_run_executor.py`
  - `tests/shared/test_import_boundaries.py`
- `python -m app.run_stats` completed successfully on **2026-04-12**
- UI-level Streamlit harness verification passed on **2026-04-12** with:
  - primary Stats surface labels `Workshop`, `Ultimate Weapons`, `Bots`, `Guardians`, `Modules`
  - no `Canonical Overview` on the main Stats workflow
  - Boss Waves runtime-basis caption present
  - sanctioned Boss Waves run showing `Max surviving wave = 130`, `First failed wave = 140`, `Rows = 14`
- refreshed full suite passed on **2026-04-12** (`390 passed`)
- refreshed Boss Waves semantic/product recertification suites passed on **2026-04-13**:
  - `pytest -q tests/simulators/test_run_executor.py` (`15 passed`)
  - `pytest -q tests/app/test_pipeline_functional.py` (`29 passed`)
  - `pytest -q tests/app/test_pipeline_ui_contracts.py` (`19 passed`)
  - `python -m app.run_stats`
- repaired current-worktree full suite passed on **2026-04-13** (`394 passed`) in **25.59s**
- corrected-recovery tranche targeted suites passed on **2026-04-11**:
  - `pytest -q tests/app/test_stats_dashboard_contract.py` -> `43 passed`
  - `pytest -q tests/app/test_pipeline_functional.py` -> `29 passed`
  - `pytest -q tests/qe/test_generic_perk_multiplier_resolution.py` -> `8 passed`
  - `pytest -q tests/qe/test_routing_checkpoint_consumer_bundle.py` -> `4 passed`
  - `pytest -q tests/simulators/test_run_executor.py` -> `15 passed`
  - `pytest -q tests/shared/test_import_boundaries.py` -> `51 passed`
  - `pytest -q tests/app/test_pipeline_ui_contracts.py` -> `19 passed`
- repaired current-worktree full suite passed on **2026-04-11** (`390 passed`) in **24.34s**
- UI-level Streamlit harness passed on **2026-04-11** with no exceptions before or after running the Boss Waves request, recovered primary Stats surfaces present (`Workshop`, `Ultimate Weapons`, `Bots`, `Guardians`, `Modules`), and Boss Waves producing `Max surviving wave = 130`, `First failed wave = 140`, `Rows = 14` for the repaired sanctioned scenario
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
