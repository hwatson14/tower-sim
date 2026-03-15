# Verification completeness status

## Current authoritative snapshot
- Package target: **simulator-complete for the intended sim scope**
- Package style: **curated AI-facing KB for ChatGPT**

## Evidence-class counts
| Evidence / class | Count |
|---|---:|
| Row-verified live source surfaces | 210 |
| Exact-rule-verified formula surfaces | 40 |
| Repo-trusted user-provided surfaces | 4 |
| Evidence-backed trusted surfaces | 250 |
| Derived non-primary classified surfaces | 56 |
| Conflict-registered classified surfaces | 3 |
| Supporting/noncanonical classified surfaces | 82 |
| Total tracked surfaces | 393 |
| Remaining unclassified surfaces | 0 |

## Package readiness note
- The package is suitable for **practical deterministic modelling** under the intended sim scope.
- The package is suitable for **ChatGPT theorycraft and strategy support** when advisory and community layers are used with canonical grounding.
- The package is not claiming exact-tick replay completeness.
- Vault closes for simulator use through explicit externalized account-input surfaces rather than silent inference.
- Same-tick precedence is intentionally out of scope except for the explicit thorns-after-damage rule.
- Tournament BC rows marked unknown to community are accepted boundaries, not blockers.
- Wall Fortification unlock is resolved in-package as **Tier 14 / Wave 60**.

## Curation note
- Canonical truth lives primarily in `kb/**/tables/**` and `kb/**/contracts/**`.
- Boundary and package-canon decisions live in the control-plane and boundary ledgers.
- Strategy and community layers are retained for practical guidance but must not override canonical mechanics.
- Notes and sources are secondary explanatory or provenance material and must not override canonical surfaces.
