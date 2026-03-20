# Accepted Variances and Limits

This file records things that are not blockers for the current frozen baseline but should be known by future AIs.

## 1. External validation coverage is incomplete
Only a subset of surfaces have direct EP comparison coverage.
Many surfaces are validated by:
- KB mapping
- formula-family governance
- contributor sanity
- audit checks
- internal consistency

This is acceptable for the current baseline, but it means future external validation can still improve confidence.

## 2. Some surfaces are non-comparable by nature
Certain runtime/mechanic/capability surfaces do not have a clean EP comparator or do not map one-to-one with workbook exports.
That is not a bug by itself.

## 3. KB alignment is governance-model dependent
The package now reports strict KB alignment closure under the current governance model.
Future tightening of the governance model could reopen rows without implying the current package is broken.

## 4. Count/integrality policy is now explicit for touched ambiguous perk cases
For certain count-like perks and related surfaces, explicit policy fields were added because the KB had previously been too implicit.
These are now governed, but future direct game telemetry could still refine them.

## 5. Runtime-family surfaces depend on upstream resolved surfaces
Some runtime-composed surfaces depend on upstream resolved values being available first.
This is acceptable in the current execution order but should remain explicit in future refactors.

## 6. Canonical output staleness risk
If future code changes are made without refreshing:
- `out/`
- `FINAL_AUDIT_SUMMARY.*`
- `FINAL_ALL_CALCULATED_STATS.*`

then the package can become “working but stale.”
This is a process risk, not a current baseline defect.
