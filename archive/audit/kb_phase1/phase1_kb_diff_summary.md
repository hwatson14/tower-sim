# Phase 1 KB Diff Report (new KB zip vs v56 + repo readiness)

## Scope
Phase 1 only: unzip, deterministic inventory, and structured diff planning.
No runtime code paths were modified.

## Inputs
- New source-of-truth zip: `tower_kb_frozen_regenerated.zip`
- Reference zip: `tower_kb_unified_v56_labs_workshop_massive_sweep.zip`

## Archive inventory
- New zip file count: 636
- v56 zip file count: 520

## New vs v56 diff summary
- New-only paths: 229
- Removed paths (present in v56 only): 113
- Changed common paths: 97

### KB-only delta counts (new vs v56)
- New-only KB paths: 224
- Removed KB paths: 38
- Changed KB paths: 86

### New-only KB domains (new vs v56)
- `bots`: 5
- `cards`: 2
- `combat`: 1
- `economy`: 5
- `enemies`: 29
- `formulas`: 6
- `guardians`: 14
- `labs`: 19
- `ledgers`: 7
- `modules`: 3
- `tournaments`: 1
- `ultimate-weapons`: 64
- `workshop`: 68

### Changed KB domains (new vs v56)
- `advisory`: 5
- `bots`: 5
- `cards`: 3
- `combat`: 4
- `economy`: 5
- `enemies`: 3
- `global-rules`: 20
- `guardians`: 5
- `index.md`: 1
- `labs`: 11
- `ledgers`: 12
- `modules`: 2
- `perks`: 1
- `tournaments`: 2
- `ultimate-weapons`: 4
- `workshop`: 3

## New KB vs current repo readiness
- New KB files in archive: 620
- Already present in repo: 222
- Missing from repo: 398
- Present but content-different vs repo: 61

### Missing new KB domains (not in repo yet)
- `advisory`: 29
- `bots`: 9
- `cards`: 9
- `combat`: 8
- `community`: 3
- `economy`: 10
- `enemies`: 44
- `formulas`: 6
- `global-rules`: 21
- `guardians`: 18
- `labs`: 32
- `ledgers`: 13
- `modules`: 22
- `perks`: 4
- `tournaments`: 20
- `ultimate-weapons`: 78
- `workshop`: 72

### Changed new KB domains (present in repo but stale)
- `bots`: 4
- `cards`: 2
- `combat`: 3
- `economy`: 3
- `enemies`: 2
- `global-rules`: 16
- `guardians`: 3
- `index.md`: 1
- `labs`: 8
- `ledgers`: 12
- `modules`: 1
- `ultimate-weapons`: 3
- `workshop`: 3

## Proposed bounded import slices (Phase 2+)
1. **Contract and registry slice**
   - Focus on `kb/*/contracts/**`, `kb/global-rules/**`, and index/routing files needed for naming and stage/composition governance.
   - Goal: align contract surfaces first while preserving fail-closed behavior.
2. **Tables/formulas/ledger slice**
   - Import `kb/*/tables/**`, formula/ledger surfaces, and supporting raw-source mirrors.
   - Goal: update canonical data surfaces without evaluator/runtime rewrites.
3. **Validation and cleanup slice**
   - Integrate notes/validation-facing files only when required for deterministic checks.
   - Remove superseded references where replacement is explicit.

## Deliverables produced in this phase
- `audit/kb_phase1/new_kb_missing_in_repo.csv`
- `audit/kb_phase1/new_kb_changed_vs_repo.csv`
- `audit/kb_phase1/phase1_kb_diff_summary.md` (this report)

## Deterministic command footprint
- unzip both archives to isolated temp directories under `/tmp/towersim_kb_compare`
- compare by relative path + SHA-256 content hash
- aggregate deltas by KB domain for bounded import planning
