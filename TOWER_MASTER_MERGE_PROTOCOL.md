# Tower Master Merge Protocol

## Purpose
This protocol governs all future merges into the cleaned `tower_stat_calc_r37` baseline. Its purpose is to preserve calculator truth, prevent scope contamination, reduce AI merge errors, and ensure every accepted change is attributable, reviewable, and regenerable.

## Baseline identity
The current baseline is a combined:
- KB
- stat calculator
- perk timeline layer
- progression/scenario foundation
- downstream optimizer interface bundle

This is **not** a generic repo. It is a governed implementation baseline.

## Core merge principle
Default action is **reject or quarantine**, not auto-merge.

Incoming content must prove one of the following:
1. It fixes a verified defect
2. It adds approved missing scope
3. It improves governance, traceability, or reproducibility without altering mechanics
4. It restructures code only if behavior is provably unchanged

## Authority order
When sources conflict, resolve in this order unless explicitly overridden by you:

1. Current cleaned baseline implementation
2. Current shipped outputs and rebuild path
3. Baseline governance docs that define scope, boundaries, and accepted exclusions
4. Verified bug ledgers / explicit review decisions from this workstream
5. Tower Wiki for mechanics reference
6. Effective Paths or other external validation artifacts for comparison and enrichment
7. Incoming repo/package assertions
8. AI-generated commentary without runnable or cited support

## Golden truths
These are protected and cannot be silently overwritten:
- `out/` is the canonical shipped output bundle
- `python run_stats.py` is the canonical rebuild path
- The baseline's current tests are required to pass after every accepted merge
- New files are not added unless justified against existing architecture
- No incoming package may silently widen scope claims in docs/manifest without explicit approval
- No unresolved factual conflict may be hidden by doc wording

## File precedence matrix

| File / Surface Class | Precedence | Merge Default | Notes |
|---|---:|---|---|
| Runtime engine code | High | Reject unless defect fix or approved scope | Must show behavior reason |
| KB canonical tables | High | Reject unless source-truth backed | No speculative rows |
| Parser/compiler logic | High | Reject unless verified | Can silently corrupt many stats |
| `run_stats.py` and rebuild surfaces | High | Reject unless clearly beneficial and verified | Protected execution path |
| `out/` outputs | High | Regenerate, never hand-edit | Output is consequence, not source |
| Tests | High | Prefer accept | But reject tests that encode wrong behavior |
| Governance docs | Medium-high | Accept if truthful and aligned | Cannot overclaim completeness |
| AI handover docs | Medium | Accept if accurate | Must match real package contents |
| Experimental modules | Low | Quarantine first | Merge only after scope approval |
| Alternate repos/legacy snapshots | Low | Extract scope only | Never trust wholesale |

## Intake classes
Every incoming package/change must be classified before merge.

### Class A — Safe governance/hygiene
Examples:
- manifest/readme truthfulness corrections
- inventory docs
- control-plane cleanup
- comments, notes, handover artifacts

Default: **accept after quick verification**

### Class B — Verified defect fix
Examples:
- incorrect stat routing
- wrong promotion to canonical stat
- bad perk application
- broken progression formula

Default: **accept only with proof**
Required proof:
- defect statement
- changed files
- why old behavior is wrong
- why new behavior is right
- tests or deterministic verification

### Class C — Approved missing scope
Examples:
- scenario engine expansion
- boss TTK closure
- new canonical stats or mechanics

Default: **quarantine first**
Required proof:
- scope statement
- boundary statement
- dependencies
- no duplicate ownership with existing layer
- verification plan

### Class D — Refactor/restructure
Examples:
- file moves
- naming cleanup
- architectural reshaping

Default: **reject unless merge pain clearly reduced and behavior preserved**
Required proof:
- reason existing structure is insufficient
- unchanged behavior evidence
- updated references/docs/tests

### Class E — External extract only
Examples:
- buggy repo with some useful scope hidden inside
- Codex package with partial features

Default: **never wholesale merge**
Action:
- extract scope
- rewrite to baseline standards
- merge only as discrete slices

## Merge admission checklist
A change is admissible only if all applicable items pass.

| Check | Required | Pass rule |
|---|---:|---|
| Classified into intake class | Yes | A/B/C/D/E assigned |
| Scope statement provided | Yes | What changes and what does not |
| Ownership conflict checked | Yes | No duplicated layer ownership |
| File impact listed | Yes | All touched files identified |
| Existing file preferred over new file | Yes | New file explicitly justified |
| Rebuild path preserved | Yes | `run_stats.py` still canonical |
| Tests pass | Yes | Existing tests green |
| Output regen clean | Yes | `out/` regenerated successfully |
| Docs truthful | Yes | No false completeness claims |
| Contradictions surfaced | Yes | Conflicts stated, not buried |

## Hard rejection rules
Reject immediately if any of the following occur:
- package asks to merge entire alternate repo wholesale
- docs claim scope not actually implemented
- outputs are hand-edited instead of regenerated
- runtime behavior changes with no explicit defect or scope case
- new files added without architectural justification
- tests are removed or weakened to make a merge pass
- mechanics are asserted without baseline support, wiki support, or deterministic proof
- incoming content mixes cleanup and mechanics changes without separation

## Quarantine rules
Quarantine instead of reject when content may be useful but is unsafe to merge directly.

Quarantine buckets:
1. Scope extract candidates
2. Suspected good ideas with weak implementation
3. Validation-only artifacts
4. Experimental mechanics not yet accepted into baseline ownership

## Merge workflow
1. Identify incoming package/change
2. Classify into A/B/C/D/E
3. Produce file delta map
4. Separate governance vs implementation vs outputs
5. Reject wholesale merge if mixed-risk bundle
6. Extract only admissible slices
7. Apply changes into baseline style and architecture
8. Run tests
9. Run canonical rebuild
10. Review regenerated outputs and changed docs
11. Record decision log: accepted / quarantined / rejected

## Decision log schema
For each future intake, record:
- intake name
- date
- class
- claimed purpose
- accepted files
- quarantined files
- rejected files
- verification run
- unresolved risks
- next action

## Post-merge gate
A merge is not complete until all apply:
- tests pass
- rebuild passes
- outputs regenerate
- no control-plane lies introduced
- changed scope is documented truthfully
- no orphan new files
- no silent ownership conflict between layers

## Recommended working rule for future packages
Use this default posture:

- **Baseline is implementation truth**
- **Incoming repos are scope mines, not trust sources**
- **Only merge slices, never identities**
- **Regenerate outputs every time**
- **Prefer fewer touched files**
- **If boundary unclear, quarantine**

## First practical application
For the next incoming repo/package, produce this exact merge artifact set:
1. Intake classification
2. File delta map
3. Scope extraction table
4. Accept / quarantine / reject decision table
5. Required verification steps
6. Recommended merge order

