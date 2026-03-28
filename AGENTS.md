# AGENTS.md

This repo is a KB-aligned deterministic simulator and advisory stack for The Tower. Treat it as a production codebase with an active target architecture, not a scratchpad.

## Mission

Preserve three things at all times:
1. KB truth stays authoritative.
2. Runtime ownership stays explicit.
3. AI changes stay narrow, reviewable, and reversible.

Do not invent mechanics, aliases, caps, formulas, routing, or architecture. If the KB, code, and tests disagree, stop and resolve the mismatch before extending behavior.

## Current architecture

The live package spine is:
1. `input/` - imports, parsing, manual inputs, runtime-state assembly
2. `qe/` - query engine authority, routing, contracts, stat resolution, compilers
3. `simulators/` - progression, timing, scenario, perk timeline, incremental simulation
4. `evaluators/` - scoring, comparison, objectives, ranking
5. `advisors/` - recommendation and upgrade advice
6. `app/` - thin entrypoint, pipeline wiring, display
7. `kb/` - authoritative mechanics, tables, contracts
8. `tests/` - verification
9. `out/` - committed generated outputs used by workflows and tests

Dependency direction:

`app -> advisors -> evaluators -> simulators -> qe -> input`

`qe` may also depend on `kb/`.

Transitional surfaces:
- root `run_stats.py` is legacy domain/helper code and must not become the default place for new business logic
- `optimizer/` is transitional compatibility surface; prefer `evaluators/` unless maintaining an existing shim
- archived or legacy paths are read-only unless the task is explicitly archival or migration work

## Scope control

Use these files as the execution-control stack when present:
- `ACTIVE_TRANCHE.md` - the only active implementation scope
- `ARCHITECTURE.md` - target layer model and allowed dependency shape
- `REPO_INDEX.yaml` - file-status and ownership ledger

Rules:
- Do not infer active scope from repo history, archived notes, or old worktrees when `ACTIVE_TRANCHE.md` exists.
- Do not treat `.claude/worktrees/`, `archive/`, or legacy documents as active instructions.
- Do not broaden a request into architecture work, refactors, or file moves unless the user explicitly asks.
- Do not edit unrelated dirty files to "clean things up".
- Do not add new top-level packages, registries, or orchestration layers unless the user explicitly approves an architecture change.
- Prefer the smallest viable diff in the existing owner surface.

## Ownership rules

For every mechanic-facing change, be able to answer:
1. What KB surface owns the mechanic?
2. What runtime surface consumes or resolves it?
3. What test proves it?

If you cannot answer all three, do not proceed.

One mechanic, one owner:
- `kb/` owns mechanic truth
- `qe/` owns stat/query contracts, routing, and authoritative resolution
- `simulators/` owns forward simulation behavior
- `evaluators/` owns scoring and comparison logic
- `advisors/` owns recommendation policy
- `app/` owns CLI/pipeline wiring and presentation only

Do not duplicate formulas across layers. Route to the owner.

## File placement

Place new content only in its owning surface:
- mechanic truth, tables, contracts, ledgers -> `kb/`
- imports and manual inputs -> `input/`
- authoritative resolution and routing -> `qe/`
- simulation logic -> `simulators/`
- evaluation and ranking -> `evaluators/`
- advisory policy -> `advisors/`
- entrypoint/pipeline/display wiring -> `app/`
- verification fixtures and tests -> `tests/`
- generated outputs -> `out/`

Avoid creating new files when an existing owner file can be edited safely.

Do not create new top-level `docs/` or `config/` buckets for implementation artifacts.

## Validation

Minimum validation is proportional to risk:
- narrow cleanup: targeted checks or targeted tests
- routing or compiler changes: targeted tests for each affected consumer
- mechanic or formula changes: targeted tests plus broader regression as needed
- output changes: rebuild outputs and verify consumers

Preferred order:
1. targeted `pytest` selection
2. `python run_stats.py` or `python -m app.run_stats` when outputs or pipeline behavior are affected
3. full `pytest` for release-level or cross-layer changes

## Stop conditions

Stop and ask before proceeding if:
- the change conflicts with `ACTIVE_TRANCHE.md`
- the fix requires architecture changes, package moves, or new owner surfaces
- KB truth is missing or ambiguous
- a requested change would touch many unrelated files
- the repo has unexpected user edits in the same surface and intent is unclear

## Working standard

A good change:
- preserves KB alignment
- keeps ownership unambiguous
- stays inside the requested scope
- updates the smallest necessary tests
- leaves the repo easier to reason about

A bad change:
- invents mechanics or defaults
- copies logic instead of routing to the owner
- uses archived structure as if it were live
- expands a small task into a refactor
- changes outputs without rebuilding or validating them
