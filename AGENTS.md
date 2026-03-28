# AGENTS.md

This repo is a KB-aligned deterministic simulator and advisory stack for The Tower. Treat it as a production codebase with an active target architecture, not a scratchpad.

## Mission

Preserve three things at all times:
1. KB truth stays authoritative.
2. Runtime ownership stays explicit.
3. AI changes stay narrow, reviewable, and reversible.

Do not invent mechanics, aliases, caps, formulas, routing, or architecture. If the KB, code, and tests disagree, stop and resolve the mismatch before extending behavior.

## Shared instruction model

This file is the shared repo contract for coding agents.
- Codex reads this file directly.
- Claude project instructions should import this file instead of duplicating it.
- Do not maintain separate repo-level rule sets for different agents unless a tool-specific exception is truly required.

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
10. `archive/` - inactive history and handoff material; not active implementation surface

Dependency direction:

`app -> advisors -> evaluators -> simulators -> qe -> input`

`qe` may also depend on `kb/`.

Archived and legacy paths are read-only unless the task is explicitly archival or migration work.

## Scope control

Use these files as the execution-control stack when present:
- `ACTIVE_TRANCHE.md` - the only active implementation scope
- `ARCHITECTURE.md` - target layer model and allowed dependency shape
- `REPO_INDEX.yaml` - file-status and ownership ledger

Rules:
- Do not infer active scope from repo history, archived notes, or old worktrees when `ACTIVE_TRANCHE.md` exists.
- Do not treat `.claude/worktrees/`, `archive/`, or legacy documents as active instructions.
- Do not broaden a request into architecture work, refactors, or file moves unless explicitly asked.
- Do not edit unrelated dirty files to "clean things up".
- Do not add new top-level packages, registries, or orchestration layers unless explicitly approved.
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

## RTK shell discipline

Default shell rule:
- Prefix shell commands with `rtk` whenever that preserves the intended behavior.
- Assume `rtk` is the default path for git, search, test, build, and diagnostic shell commands.

Required workflow for repo tasks:
1. Narrow scope first with compact commands such as `rtk git status`, `rtk rg`, `rtk grep`, `rtk ls`, or `rtk find`.
2. Identify the exact file and exact symbol or block before reading or editing.
3. Avoid broad scans and avoid reading large files in full unless explicitly required.
4. After patch and narrow verification, stop.
5. Do not continue into adjacent cleanup, refactors, or new tranches unless explicitly instructed.

Examples:
- search: `rtk rg "pattern" input qe tests`
- tests: `rtk pytest -q tests/qe/test_contracts_models_smoke.py`
- git diff: `rtk git diff -- app/run_stats.py`
- pipeline run: `rtk python -m app.run_stats`

Notes:
- RTK helps with shell command output. It does not govern built-in file-read tools.
- Therefore, do not compensate for missing shell compression by scanning more files.
- If `rtk` changes command semantics for a task, state that explicitly and use the minimum necessary non-RTK command.

## File placement

Place new content only in its owning surface:
- mechanic truth, tables, contracts, ledgers -> `kb/`
- imports and manual inputs -> `input/`
- authoritative resolution and routing -> `qe/`
- simulation logic -> `simulators/`
- evaluation and ranking -> `evaluators/`
- advisory policy -> `advisors/`
- entrypoint, pipeline, display wiring -> `app/`
- verification fixtures and tests -> `tests/`
- generated outputs -> `out/`
- inactive history and handoff material -> `archive/`

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
2. `python -m app.run_stats` when outputs or pipeline behavior are affected
3. full `pytest` for release-level or cross-layer changes

When reporting validation, distinguish:
- what was run
- what passed
- what was intentionally not run

## Stop conditions

Stop and ask before proceeding if:
- the change conflicts with `ACTIVE_TRANCHE.md`
- the fix requires architecture changes, package moves, or new owner surfaces
- KB truth is missing or ambiguous
- the requested change would touch many unrelated files
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
