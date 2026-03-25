# AGENTS.md

This repo is a KB-aligned deterministic simulator and calculator stack for The Tower. Treat it as a working core, not a document shelf.

## Operating model

The repo truth model is:
1. mechanic truth in `kb/`
2. state compilation in `parsers/`, `compilers/`, and `models/`
3. implementation in `engine/`, `optimizer/`, and `run_stats.py`
4. verification in `tests/`
5. generated artifacts in `out/`

Do not invent mechanics, aliases, caps, or formulas. If the KB and code disagree, stop and resolve the mismatch before adding more code.

## Execution control

When the repo contains the control stack files below, use them as the execution system for Codex work:
- `AI_EXECUTION_PLAN.md` = canonical whole-program plan
- `ACTIVE_TRANCHE.md` = only active implementation scope
- `BURNDOWN.yaml` = live phase/tranche delivery and verification state

Rules:
- Do not infer active scope from the execution plan alone when `ACTIVE_TRANCHE.md` exists.
- Do not treat `BURNDOWN.yaml` dependencies or phase gates as advisory; respect them as ordering constraints.
- All work is phase-gated: all tranches in the current phase must complete before the next phase begins.
- Parallel work is allowed only across tranches inside the same phase and only when they do not touch the same owner surfaces.
- Update tranche and burndown state when work changes their truth.

## Core commands

Install editable dev environment:

```bash
pip install -e .[dev]
```

Rebuild current outputs:

```bash
python run_stats.py
```

Run validation:

```bash
pytest
```

## Repo shape

- `kb/`: authoritative mechanics, tables, contracts, notes, ledgers
- `input/`: manual assumptions (`assumptions.yaml`), perk config, and import slot (`input/imports/` for IDS/Progress/EP_Export CSVs)
- `parsers/`: raw IDS parsing
- `compilers/`: account-state and stat-input compilation
- `models/`: strongly-typed runtime structures
- `engine/`: stat engine, scenario/timing, progression, perk timeline, geometry, incremental systems
- `optimizer/`: scoring and path ranking
- `scripts/`: small workflow helpers
- `templates/`: static assets required by tests and geometry workflows
- `tests/`: regression and contract coverage
- `out/`: committed generated outputs used by current tests and workflows

## Artifact placement and file-creation rules

Top-level `docs/` and `config/` are retired generic buckets and are banned destinations for new files unless the user explicitly approves a specific exception.

Do not place any of the following in `docs/` or `config/`:
- tranche notes
- ownership ledgers
- dependency CSVs
- temporary analysis artifacts
- governance ledgers
- local KB explanatory notes

Place artifacts in the owning surface:
- canonical mechanic truth -> `kb/`
- canonical governance, ledgers, and contracts -> `kb/ledgers/` or `kb/contracts/` or the owning KB directory
- runtime inputs and manual assumptions -> `input/` (manual config in `assumptions.yaml`; imported CSVs in `input/imports/`)
- runtime-generated artifacts -> `generated/`
- code-owned runtime assets -> owning code directory
- test fixtures and verification assets -> `tests/`
- generated outputs -> `out/`
- tranche-scoped execution analysis -> `ACTIVE_TRANCHE.md` unless a separate canonical owner clearly exists

Before creating a new file, determine all of the following:
1. artifact type
2. owner surface
3. permanence (`permanent`, `tranche_scoped`, `generated`, or `disposable`)
4. why an existing file is insufficient
5. deletion condition for any non-permanent artifact

Prefer editing an existing owner file over creating a new one.

Do not create standalone tranche-analysis files by default.

If tranche analysis is needed, prefer:
1. folding durable conclusions into `ACTIVE_TRANCHE.md`
2. folding canonical conclusions into an existing KB-owned file
3. deleting the analysis artifact once the implementation decision is captured

All new filenames must follow naming v2:
- no tranche/history prefixes such as `phase2`, `phase2a`, `tranche3`, `migration`, `temp`, or `new`
- no numbered sequencing prefixes such as `01_` or `42_`
- filename describes owned surface or purpose, not implementation history
- prefer concise domain-first names
- use `README.md` for local explanatory notes in an owning directory
- use ledger/policy names for structured governance files under `kb/ledgers/`
- do not use `contract` in a filename unless the file is a true canonical contract surface

Before calling work complete, verify all of the following:
- no new files were created under retired `docs/` or `config/`
- any tranche-scoped conclusions were folded into the correct control file or deleted
- any new file has a clear owner and lifetime
- no stale references remain to retired paths
- the repo still reads like a coherent operating core

## Hard rules

### 1. KB alignment is mandatory

Every mechanic-facing change must answer:
- what KB surface owns this mechanic?
- what runtime surface consumes it?
- what test proves the behavior?

If you cannot answer all three, do not merge the change.

### 2. Fail closed

If a required input, table, alias, dependency edge, or output artifact is missing, raise or stop. Do not silently fallback to guessed values.

### 3. One mechanic, one owner

Do not duplicate mechanic ownership across files. A surface may aggregate, route, or display a value, but one implementation point must own the logic.

### 4. No code-first invention

Do not add new files, new registries, or new architecture layers unless the existing repo shape is demonstrably insufficient. Prefer editing an existing owner.

### 5. Preserve deterministic outputs

Given the same committed inputs, the repo should emit the same outputs. Avoid hidden state, time-based behavior, network dependencies, or random behavior without explicit seeded control.

## Change classification

Classify each change before editing:
- **KB correction**: mechanic truth, table content, alias or contract fix
- **Routing correction**: wrong surface ownership, bad import path, wrong source table, stale resolver
- **Formula correction**: arithmetic or semantic bug in a mechanic owner
- **Output correction**: emitted artifact schema, destination routing, display/output mapping
- **Test correction**: missing or stale test after a real code change
- **Cleanup only**: repo hygiene with no mechanic change

State the classification in your PR, note, or handover summary.

## Validation expectations

Minimum validation depends on the change:

- Cleanup only: targeted grep/checks plus affected tests
- Import/routing changes: targeted tests for every moved consumer
- Formula/mechanic changes: targeted tests plus broader regression where risk justifies it
- Output-schema changes: rebuild `out/` and run smoke/consumer tests

Preferred order:
1. targeted unit tests
2. `python run_stats.py`
3. full `pytest`

## Editing rules

- Keep imports local and explicit.
- Prefer small diffs over broad rewrites.
- Do not rename core surfaces casually.
- Do not delete committed outputs in `out/` unless you rebuild them in the same tranche.
- Do not move KB files unless the change is a deliberate KB refactor.
- Avoid introducing compatibility shims unless a real consumer still needs them.

## Perk timeline subsystem

The perk timeline subsystem now lives in `engine/`:
- `engine/perk_timeline_generator.py`
- `engine/perk_tables.py`

It resolves canonical perk tables directly from `kb/perks/tables/`.
Do not reintroduce a separate top-level loader package or a dead `tables/` manifest layer.

## Packaging and execution

This project is run primarily through `run_stats.py` and direct module imports. Keep packaging simple. Do not add framework ceremony unless there is a concrete runtime need.

## What good changes look like

A good change:
- preserves or improves KB alignment
- reduces ownership ambiguity
- avoids duplicate logic
- keeps the repo easier for Codex to extend
- adds or updates the smallest necessary validation

A bad change:
- adds a new layer because it feels cleaner
- duplicates a formula instead of routing to the owner
- preserves stale files “just in case”
- changes outputs without rebuilding and validating them
- leaves tests or docs pointing at retired surfaces

## Delivery standard

Before calling work complete, check all of the following:
- imports resolve
- targeted tests pass
- `python run_stats.py` succeeds when relevant
- `pytest` passes for release-level changes
- no stale references remain to retired paths touched by the change
- the repo still reads like a coherent operating core
