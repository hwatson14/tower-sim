# TowerSim Bible v49 Reconciliation Review

Status: Audit companion to the active v49 bible  
Date: 2026-04-09  
Purpose: prove that the new bible is a deliberate consolidation rather than a drift event

---

## R0. Review purpose and method

This file is not a second authority.

It exists to answer four review questions explicitly:

1. What sources were checked?
2. What was preserved from v47/v48?
3. What was intentionally changed or removed?
4. Is v49 safe to use as the single active authority for Codex?

### Review rules

- no silent loss of controlling content
- no silent widening beyond the user-locked scope
- no stale v48 statements carried forward as if they were still current repo truth
- no second kernel-authority left alive
- no repo edits assumed; this review only audits the markdown output

### Pass / fail standard

Pass only if all are true:

- every major control concept from v48 has a home in v49, or is explicitly removed with reason
- the latest repo deltas that matter are captured
- the new scope is explicit and bounded
- no unresolved contradictory authority remains

---

## R1. Source corpus inventory

### R1.1 Files reviewed directly

- `TowerSim_bible_v47.md`
- `TowerSim_bible_v48.md`
- latest uploaded repo `tower-sim-src.zip`
- extracted repo snapshot under `/mnt/data/tower_repo`
- repo files inspected directly:
  - `ACTIVE_TRANCHE.md`
  - `BURNDOWN.yaml`
  - `ARCHITECTURE.md`
  - `README.md`
  - `AGENTS.md`
  - `app/pipeline.py`
  - `app/streamlit_inspector.py`
  - `simulators/run_executor.py`
  - `tests/app/test_stats_dashboard_contract.py`
  - `tests/simulators/test_run_executor.py`
  - `out/run_stats_query_rows_start_of_run.json`
  - `out/run_stats_query_rows_max_progression.json`

### R1.2 Explicit user instructions incorporated

The current user-locked directives that materially shaped v49 were:

- latest uploaded repo is the active baseline
- for now, the repo target is to accurately display every stat in Streamlit and have the max-waves simulator running as defined
- performance targets, KB alignment, and removal of bloat remain in scope
- old kernel content should be consolidated into the bible, not kept as a separate authority
- only the bible markdown files are to be updated
- the new files must be reviewed explicitly for no loss, no regression, and no drift
- latest repo had slight updates fixing interest and wall rebuild issues

---

## R2. High-level change summary

### R2.1 What v49 intentionally changes

1. Replaces the old active staged program from v48 with a new single current program:
   - canonical stat visibility in Streamlit
   - max-wave simulator delivered through Streamlit
   - performance and residue cleanup required to make that usable

2. Promotes the visible-stat contract from appendix-style guidance into core active authority.

3. Absorbs useful kernel/evaluator-spec ideas into the simulator and performance sections instead of preserving a separate live companion authority.

4. Explicitly records latest-repo deltas that make parts of the old Workshop gap list stale.

5. Explicitly overrides the stale maintenance-stabilization framing in the repo governance files for the purpose of this handoff.

### R2.2 What v49 intentionally does not do

- it does not broaden scope into evaluator delivery
- it does not broaden scope into optimiser delivery
- it does not claim the whole repo is now complete
- it does not silently rewrite the repo itself
- it does not preserve a second active kernel spec

---

## R3. Preservation matrix

This matrix is keyed to the major v48 section structure and the major live concepts that mattered.

| Source | Status in v49 | Destination in v49 | Notes |
|---|---|---|---|
| v47 section 0 authority basics | carried forward | v49 sections 0, 3 | preserved, but v49 uses v48 as the stronger immediate scaffold |
| v47 section 0.5 production-spec glitch | removed intentionally | R6 repo/doc delta note | not preserved as authority because v48 fixed it |
| v48 section 0 use/version/authority discipline | carried forward | v49 sections 0, 3 | preserved materially |
| v48 evidence labels | carried forward | v49 section 0 | preserved |
| v48 ambiguity-is-a-defect rule | carried forward | v49 section 0 | preserved |
| v48 single active bible rule | carried forward | v49 sections 0, 3 | preserved |
| v48 executive summary | merged and rewritten | v49 sections 1, 2 | scope-reset but substance preserved |
| v48 real usage model | carried forward | v49 section 2 | preserved |
| v48 streamlit-as-core-observability stance | strengthened intentionally | v49 sections 2, 8 | now Streamlit-first operational surface |
| v48 product goal / near-term goal | rewritten | v49 sections 1, 8 | widened to include simulator delivery in current scope |
| v48 repo shape / file maps | narrowed intentionally | v49 section 3 | no need to restate every file inventory in the active bible; ownership model preserved |
| v48 target architecture | carried forward | v49 sections 2, 3, 6 | preserved at the level needed for current scope |
| v48 measured current health | merged | v49 sections 3, 4, 5, 12 | repo truths preserved; stale parts corrected |
| v48 live bugs list | narrowed intentionally | v49 sections 7, 8, 9 | only the items relevant to current scope remain active in main authority |
| v48 Workshop completeness narrative | rewritten | v49 sections 4, 8, 12 | old gap list preserved only as historical context; latest repo delta recorded |
| v48 performance conclusions | carried forward | v49 section 6 | preserved |
| v48 performance targets `<50ms` / `<100ms` | carried forward | v49 section 6 | preserved explicitly |
| v48 decisions D-01 to D-14 | carried forward | v49 sections 1 through 8 | preserved materially |
| v48 realizations R-01 to R-11 | merged | v49 sections 2, 6, 7 | preserved as governing logic, not as separate list |
| v48 backend model / database-style nuance | carried forward | v49 sections 2 and 6 | preserved in shorter form |
| v48 recommended next work order | replaced intentionally | v49 section 8 | replaced because active program changed |
| v48 blind Codex continuation mode | replaced intentionally | v49 sections 8 and 12.5 | old T1/T2/T3 staging no longer active |
| v48 active authority order | carried forward | v49 section 3 | preserved and sharpened |
| v48 stop rules | carried forward | v49 section 8.9 and section 10 | preserved |
| v48 governance-sync rule | carried forward | v49 sections 3, 7, 9 | preserved |
| v48 current one-paragraph summary | carried forward | v49 section 11 | preserved in updated form |
| v48 formal visible-stat contract appendix | carried forward and promoted | v49 section 4 | this is one of the most important preserved elements |
| v48 workshop hardening specifics | carried forward | v49 section 4 | preserved materially |
| v48 deprecated-authority ledger | merged | v49 sections 7, 10, appendix 12 | preserved in simplified form |
| v48 measured performance appendix | merged | v49 section 6 and appendix 12 | preserved materially |
| v48 domain rollout ledger | rewritten | v49 sections 4 and 8 | old rollout order no longer active as written |
| v48 non-goals / anti-scope rules | carried forward | v49 sections 1.3, 10 | preserved |
| v48 reproducible benchmark appendix | carried forward | v49 section 6 and appendix 12.3 | preserved materially |
| v48 precise QE migration plan appendix | merged and narrowed | v49 sections 6, 7, 8 | preserved as direction, not as a separate appendix |
| v48 document lineage / residual limits | narrowed intentionally | this review file | moved here rather than bloating active authority |
| v48 incorporated external evaluator proposal | narrowed intentionally | v49 sections 5, 10 | only the useful clauses relevant to current scope remain |
| v48 external-execution limit re-pass | narrowed intentionally | v49 sections 6 and 10 | preserved only where still relevant to current scope |
| v48 repo completion contract | rewritten | v49 sections 1 and 9 | completion now scoped to current program |
| v48 future file inventory by stage | removed intentionally | not preserved as active content | because the current scope no longer needs future evaluator/optimiser stage file planning |
| v48 future file-role contracts | removed intentionally | not preserved as active content | same reason |
| v48 consumer cutover matrix | merged | v49 sections 5 and 7 | preserved conceptually |
| v48 legacy replacement and deletion ledger | carried forward | v49 section 7 | preserved materially |
| v48 residual future evaluator-kernel clauses | absorbed intentionally | v49 section 5 and section 6 | no separate kernel authority remains |

---

## R4. Regression review

### R4.1 Authority regression check

Result: **Pass**

Checks:
- single active bible rule preserved
- authority order preserved
- stale repo governance explicitly demoted where conflicting
- no second kernel spec left active

### R4.2 Observability-contract regression check

Result: **Pass**

Checks:
- row-status semantics preserved
- provenance rules preserved
- anti-backfill rule preserved
- Workshop retained as reference pattern
- visibility meaning sharpened rather than weakened

### R4.3 Performance-contract regression check

Result: **Pass**

Checks:
- `<50 ms` loadout delta target preserved
- `<100 ms` full stats refresh target preserved
- cold/hot split preserved
- benchmark methodology preserved
- anti-theatre rule preserved
- no forced CI/precompute dependency introduced

### R4.4 Deletion-gate regression check

Result: **Pass**

Checks:
- parity-before-deletion preserved
- no “keep it just in case” regression
- cutover/remove rule preserved

### R4.5 Streamlit-first usage-model regression check

Result: **Pass**

Checks:
- Streamlit remains primary user-facing operational surface
- Streamlit not allowed to become second engine
- Boss Waves current path acknowledged
- simulator completion explicitly tied to Streamlit

### R4.6 Workshop-regression check

Result: **Pass with update**

Checks:
- Workshop remains reference implementation
- old v48 gap list not treated as current truth
- latest repo note about `Interest / Wave` and `Wall Rebuild` incorporated
- current thorns naming change acknowledged

### R4.7 Scope-regression check

Result: **Pass**

Checks:
- evaluator/optimiser remain out of scope
- cleanup remains in scope only where relevant
- no broad platform completion claim made

### R4.8 Workflow-machinery check

Result: **Pass**

Checks:
- v49 remains the sole active product-and-scope authority
- reconciliation review remains non-authoritative
- repo-local `AGENTS.md`, Codex skills, and startup prompts are explicitly subordinate workflow machinery only
- no second design authority has been reintroduced through packaging

---

## R5. Drift review

### R5.1 Scope drift wider than requested

Result: **Pass**

v49 does not reactivate evaluator or optimiser delivery.  
It also does not silently keep the old future-stage file inventories alive as if they still governed the current scope.

### R5.2 Silent narrowing of requested goals

Result: **Pass**

v49 does not narrow the ask to “Workshop only” or “boss waves only”.  
It explicitly includes:
- every canonical user-relevant stat visible
- max-wave simulator through Streamlit
- performance targets
- bloat/authority cleanup

### R5.3 Wording drift that changes implementation meaning

Result: **Pass after rewrite**

Most important corrections made during drafting:

- replaced “Streamlit is mainly observability” with “Streamlit is the primary operational surface”
- replaced “preserve kernel spec as future asset” with “absorb kernel principles here”
- replaced older T1/T2/T3 stage wording with one current program

### R5.4 Future-stage leakage back into active authority

Result: **Pass**

Potentially dangerous future-stage material from v48 was either:
- absorbed as current guardrail if still useful, or
- removed from active authority if it only supported deferred evaluator/optimiser work

---

## R6. Repo-truth sync review

### R6.1 Latest-repo truths that changed v49 materially

Result: **Pass**

Directly observed repo facts that changed the new bible:

1. root governance still claims maintenance stabilization / hygiene completion
2. `app/streamlit_inspector.py` already has a Boss Waves operational surface
3. `app/pipeline.py` already wires boss-wave payloads through active simulator code
4. `simulators/run_executor.py` already exposes `run_to_max(...)`
5. `tests/simulators/test_run_executor.py` already covers run-to-max stepping and warm benchmark shape
6. committed query-row artifacts already include:
   - `state::economy.interest_per_wave_pct`
   - `state::wall.rebuild_seconds`
   - `state::tower.thorns_damage_pct`

### R6.2 v48 statements now treated as stale or incomplete

Result: **Pass**

The biggest stale item corrected:
- v48 still treated the three Workshop surfaces as missing QE coverage in the active completeness list

v49 explicitly downgrades that to historical context only and records that the live repo moved on at least part of it.

### R6.3 Remaining uncertainty

Result: **Explicitly labeled**

Still not freshly proven in this review:
- the exact final Streamlit rendering state for every canonical stat domain
- whether any additional current repo gaps remain beyond the inspected surfaces
- the current real measured timings on the latest repo snapshot in this environment

These are correctly left as implementation/verification work, not asserted as already complete.

---

## R7. Kernel-spec absorption review

### R7.1 Retained

Retained from the old kernel/evaluator-spec ideas because they still improve the current scope:

- normalize/validate before timed execution
- stable result schema / provenance discipline
- benchmark anti-cheat rules
- cache disclosure rules
- parity-before-cutover-and-delete rule
- bounded formula-structure guardrails
- hot-path data-layout discipline as guidance

### R7.2 Reframed

Reframed into current-scope language:

- old evaluator-kernel notions were reframed as simulator and performance guardrails
- future companion-spec governance was reframed as “no second active authority”

### R7.3 Intentionally not activated

Not activated in v49:

- evaluator delivery program
- optimiser delivery program
- future-stage file inventories for later evaluator/optimiser tracks
- separate kernel document as a living authority

### R7.4 Proof that no separate kernel authority remains

Result: **Pass**

v49 contains:
- active simulator authority section
- absorbed kernel principles
- explicit statement that there is no second active kernel spec for the current scope

---

## R8. Self-review

### R8.1 Accuracy review

Score: **9/10**

Strengths:
- new scope is explicit
- latest repo delta note was incorporated
- stale governance conflict was surfaced rather than ignored

Remaining limitation:
- not every live repo surface was re-opened end to end; the review focuses on the surfaces that matter for the new bible

### R8.2 Preservation review

Score: **9/10**

Strengths:
- major v48 governing concepts all have a home
- removed items are explicitly justified
- no silent deletion of the visible-stat contract or performance contract

Remaining limitation:
- the full fine-grained file inventory tables from v48 were intentionally not copied into v49 to keep the active authority compact

### R8.3 Strategy review

Score: **9/10**

Strengths:
- active scope matches current user instruction
- Streamlit-first stance is now explicit
- second-authority risk was reduced materially

Remaining limitation:
- v49 still relies on future repo implementation work to make every stat visible; it cannot itself prove current product completion

### R8.4 Drift / bias review

Score: **10/10**

Strengths:
- no flattering overclaim that the repo is already complete
- no false preservation of the old staged program just because it existed
- no scope widening into evaluator/optimiser territory

---

## R9. Final publish gate

### Decision

**Pass**

### Why this passes

- v49 is a coherent single active authority for the current scope
- the main stale repo/doc conflict is explicitly resolved
- useful v48 material was preserved rather than discarded
- useful kernel ideas were absorbed without leaving a second live authority
- latest repo changes relevant to the Workshop gap were explicitly recorded
- evaluator and optimiser scope remains correctly deferred

### Remaining uncertainties to keep explicit

- current measured latency values on this exact repo snapshot still need benchmark rerun
- final domain-by-domain visible coverage still needs implementation proof
- exact Streamlit product completion still needs implementation proof

### Can Codex use v49 as the single active authority?

**Yes**, for the current scoped program:
- canonical stat visibility in Streamlit
- max-wave simulator through Streamlit
- supporting performance/bloat cleanup only

---
