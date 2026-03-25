# R86 implementation scope and acceptance

> Historical note: this file is preserved as R86 handoff context. Current obligation/status truth is mapped in `AI_EXECUTION_PLAN.md`, `ACTIVE_TRANCHE.md`, and `BURNDOWN.yaml`.

## In scope
- explicit state identity binding to existing runtime/state contracts
- bounded scenario family definitions and state-mode mapping
- contributor-normalised family baseline materialisation
- immutable overlay deltas
- on-demand resolution for bounded deterministic surfaces
- contributor-ledger visibility
- dependency-aware invalidation for bounded surfaces
- `timing_v1`
- `progression_v1`

## Out of scope
- geometry ownership migration
- broad combat-helper migration
- optimiser migration
- global resolved-baseline caches
- unbounded family expansion


## Phase 1C mapped status ledger

| tracked_item | current_status | mapped_phase | mapped_tranche | owner_surface | notes |
|---|---|---|---|---|---|
| Global parity validation across declared query-owned families | open | Phase 2 | Phase 2E | parity evidence outputs for declared covered families | Remains required before Query Engine ownership completion can close. |
| End-to-end overlay and invalidation closure | open | Phase 2 | Phase 2E | query-kernel verification surfaces | Keep as explicit evidence work, not vague open-ended cleanup. |
| Residual progression bridge cleanup and stale transitional references | partially_landed_open_tail | Phase 2 | Phase 2A / Phase 2B | `compilers/stat_input_compiler.py`; `engine/progression_recalc_bridge.py` | Treat the bounded progression bridge as landed for the bounded runtime/reference path; only owner-surface cleanup remains. |
| Gate F benchmark evidence for timing + progression workloads | open | Phase 2 | Phase 2E | benchmark evidence outputs | Requires at least one timing-family and one progression-family benchmark against the reference path. |
| KB-routing authority extraction from `compilers/stat_input_compiler.py` into Query Engine ownership | open | Phase 2 | Phase 2A / Phase 2B | `compilers/stat_input_compiler.py`; Query Engine owner surfaces | Starts with function-level ownership classification before any approved extraction. |

### Status notes after `a97f469` / `d278c18`
- Treat progression recalc ownership migration as landed for the bounded progression runtime/reference path.
- Keep the thread focused on remaining acceptance evidence and stale-transition cleanup rather than redoing already-landed bridge work.
- Audit `engine/progression_recalc_bridge.py` wording against the current tests when touching bridge-adjacent notes or handoff text.

## Acceptance gates
### Gate A: contract integrity
- all new stat-query contracts layer onto existing runtime/state contracts
- no duplicate state authority introduced

### Gate B: baseline determinism and immutability
- identical `(account_snapshot_id, loadout_id, scenario_id, runtime_branch_id, family_id)` inputs produce identical baseline contributor maps
- emitted baseline maps are immutable and overlay-free

### Gate C: contributor-ledger visibility
- query responses for phase-1 important surfaces can return contributor rows and dependency trace
- contributor rows include source class, composition stage, active flag, gate reason, provenance

### Gate D: timing correctness
For governed timing scenarios, query outputs must respect:
- tournament implies perks disabled
- package chance card on/off assertions
- wave accelerator on/off assertions
- assist slot module/domain assertions
- GComp timing support surface ownership and trace

### Gate E: progression value
- bounded progression updates must avoid broad recomputation where phase-1 baseline materialisation already covers the requested family
- runtime consumers for attack/health wave remain explicitly governed

### Gate F: benchmark value
- phase-1 implementation must demonstrate positive speed value on at least one timing-family workload and one progression-family workload against the current reference path

## Materialiser seam decision
Phase 1 must:
- reuse existing compiler-emitted rows
- normalize those rows into bounded family baseline contributor maps

Phase 1 must not:
- rewrite the full compiler first
- emit giant repo-wide baseline artifacts

Compiler refactor may happen later only if the bounded baseline materialiser proves insufficient.

## Phase 1C disposition
- The tracked items above are now mapped to current phase/tranche work rather than left as free-floating R86 status notes.
- This file remains useful as acceptance framing, but it is no longer the active execution ledger.
