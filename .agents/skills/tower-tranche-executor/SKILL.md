---
name: tower-tranche-executor
description: Execute one bounded TowerSim tranche, phase task, or scoped patch using the v49 Bible, the reconciliation review, existing owner files, and explicit verification gates. Use for real implementation work with clear scope. Do not use for broad strategy, open-ended cleanup, or multi-phase programs.
---

# Purpose

Use this skill to execute one bounded TowerSim implementation task without widening scope, inventing new authority, or skipping required verification.

# Preconditions

Before using this skill, run `tower-authority-check` or perform the equivalent authority preflight.

Do not start implementation until owner, phase, no-regression constraints, and verification are explicit.

# Use when

Use this skill for:

- one phase task from Bible Section 8
- one scoped patch
- one product-surface change
- one stats visibility task
- one simulator-path task
- one truth-sync change tied to current scope

# Do not use when

Do not use this skill for:

- repo-wide redesign
- “clean up everything” tasks
- evaluator or optimiser delivery
- open-ended exploration
- any task whose owner or scope is still ambiguous

# Core execution rules

1. Work from `TowerSim_bible_v49.md` as product-and-scope authority.
2. Use live repo code, tests, and committed/generated artifacts as implementation-reality authority.
3. Use `TowerSim_bible_v49_reconciliation_review.md` to preserve intent and avoid regression. Do not treat it as a second design authority.
4. Prefer editing existing owners over adding files.
5. Do not create a new file unless the user explicitly approves it or the need is explicitly justified against owner/path rules.
6. Do not make Streamlit a second engine.
7. Do not use UI-local backfill to hide missing QE or simulator truth.
8. Do not widen into evaluator or optimiser work.
9. Do not preserve duplicate authority “just in case” once parity is proven.

# Required process

Follow this sequence exactly.

## 1. Restate scope
State:
- what this task is trying to change
- what is out of scope
- what phase from Bible Section 8 it belongs to

## 2. Name the owner path
State:
- which layer owns the change
- which files are first-touch
- which files are forbidden unless evidence forces expansion

## 3. Name the no-regression constraints
State the relevant constraints from the reconciliation review before editing.

## 4. Gather only the required evidence
Inspect only the smallest set of files, tests, and artifacts needed to execute correctly.

## 5. Implement the minimum valid change
Make the narrowest change that satisfies the acceptance criteria.

Rules:
- no speculative cleanup unrelated to the task
- no opportunistic reshaping of neighboring systems
- no hidden compatibility shortcuts

## 6. Run required verification
At minimum, use the gates named by the authority preflight.

If the task touches current-scope publish work, include the relevant v49 command gates where applicable:

- `python -m app.run_stats --perk-mode max_progression_policy --out <temp_out>`
- `pytest tests/app/test_input_dashboard_contract.py -q`
- `pytest tests/app/test_stats_dashboard_contract.py -q`
- `pytest tests/simulators/test_run_executor.py -q`

Add narrower tests for touched files, but do not replace contract gates with spot checks only.

## 7. Check against completion definition
State whether the task passed the relevant gate from Bible Section 9.

## 8. Truth-sync governance docs if required
If the task materially changes active repo truth, completion state, or active scope representation, update the necessary governance docs rather than leaving them stale.

Typical candidates:
- `ACTIVE_TRANCHE.md`
- `BURNDOWN.yaml`
- other scope-facing repo docs if they would now mislead a blind agent

## 9. Report residual blockers honestly
If something remains incomplete, say so directly.
Do not blur “patched” into “fully complete.”

# Refusal / stop rules

Stop and report rather than improvising if:

- the task would require UI-local truth invention
- the task would create a second active authority path
- the task would widen into evaluator or optimiser work
- the Bible and live repo disagree in a scope-changing way
- deletion would break an unverified consumer
- a new file appears to be the path of least resistance rather than the correct owner

# Output contract

Produce a completion report with these headings:

## Scope handled
## Owner path used
## No-regression constraints applied
## Files changed
## Verification run
## Acceptance result
## Governance docs updated
## Remaining blockers
## Any refusal or partial-completion reason

# Quality bar

A good execution is narrow, owner-correct, verified, regression-aware, and governance-aware.

A bad execution fixes the symptom while widening scope, leaves stale governance behind, or claims completion without contract evidence.
