# AGENTS.md

This file defines mandatory rules for Codex working in this repository.

This is Harry’s private personal project. Codex is the only intended editing agent. The goal is to preserve KB alignment, prevent duplicate ownership, reduce repo drift, and keep changes bounded and auditable.

## Mission

Work inside the active repo surface.

Do not invent alternate ownership, alternate formulas, alternate architecture, alternate implementation paths, or speculative mechanic behaviour when an active owner already exists.

## Repo stance

Treat this as:

- a private personal repo
- a constrained implementation environment
- a KB-aligned mechanic surface
- a repo with explicit authority rules
- a repo where archive is reference-only unless explicitly needed

Do not introduce generic OSS process, contributor ceremony, or broad housekeeping unless explicitly requested.

## Truth model

This repository uses three distinct truth layers.

### Mechanic truth
Mechanic truth is owned by the active KB and accepted canonical tables.

This includes:

- formulas
- stat composition
- timing
- progression
- scenario rules
- runtime mechanic wiring where defined by the KB
- canonical contributor ownership where the KB defines the mechanic

For mechanics, the KB and accepted canonical tables are the source of truth.

### State truth
State truth is owned by accepted active input-state surfaces.

This includes:

- account values
- labs
- workshop levels
- modules
- cards
- equipped loadouts
- inventory state
- scenario inputs
- designated active exports used as inputs

These define the state the repo is operating on. They do not by themselves define mechanics.

Generated outputs, audit artifacts, and snapshots do not automatically become state truth unless explicitly designated as active input surfaces.

### Implementation truth
Implementation truth is the current executable realization of mechanic truth and state truth.

Implementation is authoritative for what the code currently does.
Implementation is not automatically authoritative for what is mechanically true.

If implementation and mechanic truth disagree, treat that as a defect.

## KB alignment obligation

For any mechanic-affecting patch, Codex must determine which of the following applies:

1. the current implementation already aligns to the active KB
2. the current implementation does not align to the active KB and must be corrected
3. KB support is missing or incomplete, so only a temporary accepted model is possible
4. ownership or truth source is unclear and work must stop

Codex must not proceed as though existing code is sufficient proof of mechanic correctness.

## Core mechanic rule

Every mechanic-related change must be KB-backed.

This includes:

- formulas
- stat composition
- timing
- progression
- scenario rules
- runtime mechanic behaviour
- contributor wiring
- interpretation of canonical ownership where the KB defines the mechanic

KB-backed means the change can be defended by the current accepted KB or accepted canonical tables.

Do not replace missing support with plausible inference.

If KB support is missing or unclear, Codex must:

- stop and report the gap, or
- implement only if explicitly instructed to use a temporary accepted model

## No code-first or output-first justification

Do not justify a mechanic by relying only on:

- existing implementation
- passing tests
- golden outputs
- parity checks
- previous patches
- historical behaviour
- generated outputs
- audit artifacts
- observed results from prior runs

These may validate consistency.
They do not by themselves establish mechanic truth.

Do not back-solve mechanic truth from outputs alone.

## Temporary accepted models

Temporary accepted models are allowed only when explicitly intended.

They must be:

- explicitly labelled as temporary
- narrowly scoped
- clearly separated from KB truth
- easy to replace later
- validated as far as practical without overstating certainty

They must never be presented as canonical mechanic truth.

Where material, temporary accepted models must be documented in the minimum relevant active code comment or active doc so they are easy to find and remove later.

They should also state, where known:

- what KB support is missing
- why the temporary model is accepted
- what condition would allow replacement later

Unless already explicitly documented as accepted, temporary accepted models require Harry approval.

## Authority and conflict handling

Use the following interpretation model:

1. Active KB and accepted canonical tables define mechanic truth.
2. Accepted active input-state surfaces define state truth.
3. Active implementation defines current executable behaviour.
4. Tests, parity checks, audits, and golden outputs validate consistency and regression only.
5. Active root governance docs define repo rules and ownership boundaries.
6. Archive material is reference-only unless explicitly recovered and promoted.

If these surfaces disagree:

- do not silently choose
- do not paper over the difference
- do not treat consistency as proof of truth
- surface the conflict explicitly

## Active and non-active surfaces

### Active editable surfaces
These are normal candidates for patching when they are the correct owner:

- active implementation code
- active KB and canonical table surfaces
- active root governance docs
- active tests and validation surfaces

### Active but special-control surfaces
These require extra care and should not be changed casually:

- `tower-sim-data/`
- generated outputs
- golden outputs
- audit artifacts
- exported state bundles

Do not rename, restructure, or casually patch these unless the task explicitly requires it and the dependency impact has been considered.

### Non-authoritative surfaces
These are not normal patch targets:

- `archive/`
- stale or superseded docs outside the active root governance surface
- historical donor code unless explicitly recovered

## Archive rules

Anything under `archive/` is non-authoritative unless explicitly promoted.

Codex must not:

- edit files under `archive/`
- treat `archive/` as mechanic truth
- import active code from `archive/`
- patch `archive/` as part of normal implementation work
- cite archived docs as active architecture unless explicitly instructed

Archive may only be used for:

- historical reference
- targeted recovery
- donor extraction
- comparison against current implementation

Recovered material must be moved into an active authoritative path and validated before use.

## Approval gates

The following require Harry approval unless already explicitly requested in the task:

- new files
- file moves or renames
- broad refactors
- temporary accepted models not already documented as accepted
- ownership changes
- architecture changes spanning multiple active surfaces

A broad refactor includes any change that:

- touches multiple ownership surfaces
- changes public interfaces across multiple modules
- changes mechanic ownership boundaries
- restructures repo layout rather than making a local patch

## Existing-file-first rule

Before creating, moving, or splitting code:

1. identify the current active owner of the behaviour
2. patch that owner if appropriate
3. explain why that file is the correct owner

Do not create new files when an existing active owner can own the change cleanly.

## New file creation rule

New files are disallowed by default.

A new file may be created only when all of the following are true:

- no existing active file can own the change cleanly
- the new file has a clear single responsibility
- the reason for the new file is stated explicitly
- the new file will not duplicate existing ownership
- the patch explains why existing files were insufficient
- Harry approval has been given or was already explicit in the task

If this standard is not met, do not create the file.

## Ownership rule

One mechanic should have one active owner.

Do not introduce:

- duplicate formulas
- parallel implementations
- alternate calculation paths
- shadow stat composition logic
- bypass logic that silently replaces the active owner
- convenience rewrites that create second ownership

If ownership is ambiguous, stop and report the ambiguity.

## Churn control

Keep changes tight.

Do not, unless explicitly required by the task:

- rename files
- rename public symbols
- move files between directories
- reformat unrelated files
- perform opportunistic cleanup
- repair nearby unrelated defects
- create extra docs when an existing active doc should be updated
- touch generated outputs that are not part of the requested work

Do not present a mechanic change as a refactor.

## Change classification

For any non-trivial patch, classify the change as one of:

- KB-alignment fix
- implementation completion
- temporary accepted model
- refactor with no mechanic change
- documentation/governance update

If a patch does not fit clearly into one of these, stop and explain why.

## No silent mechanic changes

Any change affecting mechanics, formulas, stat composition, timing, progression, scenario behaviour, runtime behaviour, or ownership must explicitly state:

- what changed
- where it changed
- why that file owns the behaviour
- what KB or canonical table source backs the change
- what validation was performed
- whether the patch is KB-alignment, implementation, or temporary-model work
- what remains unresolved, if anything

## Fail-closed rule

When uncertain, do not guess.

Stop and report if any of the following apply:

- the active owner is unclear
- KB support is unclear or missing
- sources conflict
- archive and active code disagree
- a formula cannot be defended
- a requested change would require speculative behaviour
- a patch would create duplicate ownership

Truthful incompleteness is preferred over fabricated completion.

## Canonical commands

Use the repo’s canonical commands unless explicitly instructed otherwise.

Insert the final commands below once locked:

- setup: `python -m pip install -e .[dev]`
- main rebuild: `python run_stats.py`
- tests: `pytest`
- targeted validation: `pytest tests -q`

Do not invent alternate setup, rebuild, or validation paths just to get a patch over the line. If the canonical path fails, report the failure clearly.

## Validation rule

No non-trivial patch is complete until it is validated appropriately.

Possible validation includes:

- targeted unit tests
- parity checks
- rebuilds
- scenario checks
- audit scripts
- golden output comparison
- manual output inspection where necessary

State clearly:

- what was validated
- what was not validated
- whether any failure appears pre-existing versus patch-induced

If required validation could not be run, the patch must be reported as incomplete.

## Documentation rule

When behaviour changes materially, update the minimum relevant active documentation.

Do not produce broad doc churn. Update only the docs that directly govern or describe the changed active surface.

## Root-doc rule

Treat these root docs as active governance surfaces:

- `README.md`
- `AGENTS.md`
- `TESTING.md`
- `AUTHORITATIVE_PATHS.md`

Do not let older docs elsewhere in the repo override these unless explicitly instructed.

## Expected patch summary

For any non-trivial change, provide a short structured summary covering:

- classification
- scope
- changed files
- why those files were chosen
- KB or canonical table source of truth
- validation performed
- unresolved risks

## Default interpretation rule

If a choice exists between:

- preserving KB-backed truth but being incomplete
- appearing complete by making assumptions

choose preserving KB-backed truth.

That rule overrides convenience.
