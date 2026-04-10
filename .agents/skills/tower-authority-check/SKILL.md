---
name: tower-authority-check
description: Determine the active authority, relevant Bible sections, owner layer, scope boundaries, phase, verification gates, and governance-sync obligations before any non-trivial TowerSim work. Use for implementation, audits, fixes, cleanup, product-surface changes, or any task that could drift scope or ownership.
---

# Purpose

Use this skill to stop TowerSim work from starting on the wrong authority, wrong owner, wrong phase, or wrong scope.

This skill is the first gate for non-trivial repo work.

# Use when

Use this skill when the task involves any of the following:

- changing code
- certifying repo state
- resolving contradictions between docs and code
- touching Streamlit product behavior
- touching QE-owned stats
- touching simulator-owned logic
- changing governance docs
- cleanup or deletion decisions
- deciding which file should own a change
- anything that could widen beyond the current v49 program

# Do not use when

Do not use this skill for:

- a trivial read-only question about one file
- simple explanation of already-known behavior where no action will follow
- broad open-ended brainstorming without repo changes or decisions

# Required authority model

Apply this order strictly:

1. `TowerSim_bible_v49.md` is the active product-and-scope authority.
2. Live repo code, tests, and committed/generated artifacts are the implementation-reality authority.
3. `TowerSim_bible_v49_reconciliation_review.md` is a preservation and anti-regression companion only. It helps prevent loss, drift, and false completion claims. It is not a second product authority.
4. Root governance docs such as `ACTIVE_TRANCHE.md` and `BURNDOWN.yaml` are subordinate and may be stale.
5. Earlier bibles or companion specs are not active authority for current scope.

If product-and-scope authority and implementation-reality authority disagree in a way that changes scope, ownership, or success criteria:

- stop
- label the disagreement explicitly
- treat it as a truth-sync task
- do not improvise a hybrid answer

# Required inputs to inspect

Before answering, inspect at minimum:

- `TowerSim_bible_v49.md`
- `TowerSim_bible_v49_reconciliation_review.md`
- `AGENTS.md` if present
- the user task

Then inspect only the minimum additional repo files needed to answer the preflight questions.

# Questions this skill must answer

For the requested task, answer all of these before implementation begins:

1. What phase from Bible Section 8 is this task in?
2. Is the task in scope for v49?
3. What owner layer should own the change?
4. Which files are first-touch files?
5. Which files should not be touched casually?
6. Which Bible sections are directly relevant?
7. Which acceptance gates from Bible Section 9 apply?
8. Which governance docs will require truth-sync if the task succeeds?
9. Which reconciliation-review constraints matter for no-regression?
10. What should not be assumed?

# Output contract

Produce a compact preflight containing exactly these headings:

## Task classification
- classify the task in one line

## Phase
- state the relevant phase from Bible Section 8

## In scope / out of scope
- list what is in scope
- list what is explicitly out of scope

## Authority stack
- state the authority order for this task
- identify any live contradiction or say none found

## Owner path
- state the correct owner layer and path

## First-touch files
- list the first files that should be inspected or edited

## No-regression constraints
- list the relevant preservation constraints from the reconciliation review

## Verification gates
- list the exact tests / commands / checks that will define completion

## Governance sync required
- state whether `ACTIVE_TRANCHE.md`, `BURNDOWN.yaml`, or other governance text must be updated if the task changes repo truth

## Refusal triggers
- list what would force a stop rather than improvisation

# Quality bar

A good result from this skill makes it obvious where work should begin and what must not be guessed.

A bad result is vague, uses blended authority, misstates Bible sections, or allows work to begin without naming owner, phase, no-regression constraints, and verification.
