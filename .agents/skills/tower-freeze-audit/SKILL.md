---
name: tower-freeze-audit
description: Certify or reject a TowerSim repo state for merge, freeze, handoff, or publish based on the v49 Bible, the reconciliation review, live implementation reality, contract tests, artifact checks, benchmark evidence, and governance sync. Use for certification decisions, not for doing the implementation itself.
---

# Purpose

Use this skill to answer one question rigorously:

Is this repo state actually certifiable for the current TowerSim scope?

Allowed verdicts are:
- certified
- not certified
- partially certified for a narrower claim

Do not use reassuring language when evidence is incomplete.

# Use when

Use this skill for:

- freeze candidate review
- handoff review
- merge readiness review
- “is this really complete?” checks
- post-patch recertification

# Do not use when

Do not use this skill for:

- implementing a feature
- open-ended debugging
- architecture brainstorming
- broad cleanup unrelated to a certification claim

# Certification model

Judge the repo against:

1. `TowerSim_bible_v49.md` for active scope and acceptance definitions
2. live repo code, tests, and committed/generated artifacts for implementation reality
3. `TowerSim_bible_v49_reconciliation_review.md` for preservation, no-regression, and known hardening checks
4. touched governance docs for truth-sync accuracy

Never let stale root governance override the Bible for current scope.

# Required audit sequence

## 1. State the certification claim
Name exactly what is being certified.
Examples:
- stats completion for touched surfaces
- Boss Waves simulator delivery through sanctioned path
- scoped handoff readiness for current tranche

If the claim is vague, narrow it before proceeding.

## 2. Check scope alignment
Verify the claim is in scope for v49.
If it depends on evaluator or optimiser delivery, reject the claim as out of scope.

## 3. Check authority alignment
Verify that the touched surfaces use the sanctioned owner path.
Reject certification if success depends on:
- UI-local truth invention
- compat/report paths acting as runtime authority
- undocumented alternate execution paths
- stale governance masking current reality

## 4. Check no-regression alignment
Verify the touched work did not reintroduce a loss, drift, or contradiction that the reconciliation review had already closed.

## 5. Run required verification
Use the command set appropriate to the touched scope.
At minimum, when relevant to the claim, use:

- `python -m app.run_stats --perk-mode max_progression_policy --out <temp_out>`
- `pytest tests/app/test_input_dashboard_contract.py -q`
- `pytest tests/app/test_stats_dashboard_contract.py -q`
- `pytest tests/simulators/test_run_executor.py -q`

Add narrower tests and file inspections for the touched areas.

## 6. Check visible-surface and product-contract requirements
When relevant, verify:
- required visible surfaces are present or explicitly missing with reason
- row semantics remain explicit
- Boss Waves uses the sanctioned simulator path
- Pipeline and Checks remain diagnostics, not truth owners

## 7. Check performance claim honesty
If performance is part of the claim, require benchmark evidence from the sanctioned path.
Do not count stale committed artifacts as runtime proof.
Do not accept shortcuts banned by Bible Section 6.

## 8. Check residue and duplicate-authority status
If the claim includes cleanup or hardening, verify that:
- parity-before-deletion was respected
- no duplicate authority remains active for touched surfaces
- quarantined paths were not silently promoted

## 9. Check governance sync
If repo truth materially changed, verify that root governance docs were updated enough not to mislead a blind agent.

# Verdict rules

## Certified
Use only when:
- the claim is clearly scoped
- the owner path is correct
- required verification is green
- no blocking authority contradiction remains
- no blocking regression remains
- governance text is not materially misleading for the certified claim

## Partially certified
Use when:
- a narrower claim is proven
- but the broader claim would overstate reality

State the exact narrower certified claim.

## Not certified
Use when:
- verification fails
- evidence is incomplete
- ownership is wrong
- scope is wrong
- governance drift would mislead handoff
- performance claims depend on forbidden shortcuts
- a previously closed contradiction or drift has been reintroduced

# Output contract

Produce the audit using these headings:

## Claim under review
## Scope fit
## Owner-path check
## No-regression check
## Verification evidence
## Product-contract check
## Performance check
## Governance-sync check
## Verdict
## Blocking reasons
## Exact next steps to become certifiable

# Quality bar

A good freeze audit is decisive, scoped, evidence-backed, and regression-aware.

A bad freeze audit says “looks good” while major verification, ownership, performance, governance, or no-regression questions remain unresolved.
