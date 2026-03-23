# ACTIVE_TRANCHE

## Tranche ID
`PH3-TRANCHE-CLOSEOUT_DERIVED_SURFACES_EXIT_CERTIFICATION`

## Phase
`Phase 3 — Objective-state promotion`

## Objective
Close Phase 3 by certifying the already-landed Query Engine-owned derived objective surfaces and persistent income publication boundaries, reconciling the executed work to the phase intent, and recording an explicit Phase 3 exit decision.

## Why this tranche exists
Phase 3 implementation was not executed in the original tranche sequence, but the substantive work is largely landed. The remaining task is to turn that landed work into a defensible phase closeout rather than leaving Phase 3 open due to documentation drift, under-specified parity language, or unrelated legacy test failures.

## Change classification
- **Closeout certification**: certify the landed `derived::ehp`, `derived::edamage`, and `derived::eecon` publication/consumption path as the concrete Phase 3 outcome.
- **Control-stack reconciliation**: align tranche/burndown language with the work that actually landed rather than the tranche sequence originally imagined.
- **Evidence formalisation**: replace vague “broader parity” language with bounded per-surface evidence and an explicit exit decision.
- **Verification narrowing**: require targeted Phase 3 verification only; do not block Phase 3 on unrelated legacy test debt.

## Scope in
- reconciliation of actual landed Phase 3 work to one closeout record
- explicit certification of the governed surfaces:
  - `derived::ehp`
  - `derived::edamage`
  - `derived::eecon`
- explicit certification of persistent income publication boundaries under `derived::economy.income.*`
- confirmation that optimizer consumption is governed, query-owned, and fail-closed
- creation of a bounded Phase 3 evidence matrix
- explicit statement of maturity / accepted-model posture per derived objective surface
- explicit statement of what parity is required for Phase 3 exit versus deferred
- explicit Phase 3 exit decision recorded in control files

## Scope out
- new simulator or evaluator work
- new optimizer features or product-surface expansion
- workbook-wide or helper-by-helper exhaustive parity perfection
- fixing unrelated legacy tests outside the Phase 3 surface path
- new guessed mechanics or unsupported income models
- refactoring Phase 4+ work into Phase 3

## Required outputs
- updated `ACTIVE_TRANCHE.md` closeout tranche
- updated `BURNDOWN.yaml` reflecting the single Phase 3 closeout path
- one Phase 3 closeout note
- one Phase 3 evidence matrix covering:
  - `derived::ehp`
  - `derived::edamage`
  - `derived::eecon`
  - `derived::economy.income.*` publication boundary
- explicit maturity / evidence / known-gap entries for each governed derived objective surface
- explicit Phase 3 exit decision: `complete` or `exit_blocked`

## Required evidence matrix fields
- `surface_id`
- `owner`
- `contract_family`
- `consumer_scope`
- `maturity_label`
- `publication_status`
- `optimizer_consumption_status`
- `accepted_model_status`
- `parity_status`
- `known_gaps`
- `exit_relevance`
- `decision`

## Required verification
- targeted Phase 3 contract tests pass
- targeted Phase 3 optimizer integration tests pass
- targeted Phase 3 runtime publication validation passes
- `python run_stats.py` succeeds with the Phase 3 publication hook enabled
- no required Phase 3 surface is missing from governed publication or optimizer consumption paths

## Explicit non-requirements
- full `pytest`
- cleanup of unrelated historical test failures
- proof that every legacy helper or workbook-facing alias has perfect parity
- proof of evaluator readiness
- proof of future product-surface readiness beyond Phase 3 ownership closure

## Acceptance criteria
- the concrete Phase 3 outcome is stated plainly as governed derived surfaces rather than legacy conceptual labels
- optimizer no longer owns canonical eHP/eDamage/eEcon formulas
- derived objective and income surfaces are declared once in the governed query contracts
- a bounded evidence record exists for each required Phase 3 surface
- accepted-model posture and known gaps are explicit for each derived objective surface
- parity language is bounded to what is required for Phase 3 exit
- Phase 3 is not blocked by unrelated legacy test failures
- the closeout ends with an explicit phase exit decision rather than an open-ended note

## Exit decision rule
Phase 3 is `complete` when:
- all three governed derived objective surfaces are published and owned once
- optimizer consumption is governed and fail-closed
- persistent income publication boundaries are explicit and bounded
- targeted evidence exists for publication, contract alignment, and optimizer consumption
- any remaining gaps are explicitly recorded as accepted-model or deferred items rather than hidden blockers
- no remaining blocker belongs to Phase 3 rather than a later phase

Phase 3 is `exit_blocked` only when:
- a required governed surface is missing or multiply-owned
- optimizer still re-derives canonical objective truth locally
- required targeted verification fails
- the remaining gap is truly a Phase 3 ownership/evidence defect rather than general repo debt

## Phase 3 closeout note
Phase 3 closes on the concrete Query Engine-owned derived surface path that is already landed, not on a broader workbook-wide parity ideal. The exit decision is bounded to governed publication, contract ownership, optimizer consumption, persistent-income publication boundaries, and targeted runtime evidence for `derived::ehp`, `derived::edamage`, `derived::eecon`, and `derived::economy.income.*`.

## Phase 3 evidence matrix
```yaml
phase3_evidence_matrix:
  - surface_id: derived::ehp
    owner: canonical_query_engine
    contract_family: derived_v1
    consumer_scope:
      - optimizer
    maturity_label: accepted_model
    publication_status: pass
    optimizer_consumption_status: pass
    accepted_model_status: explicit
    parity_status: bounded_pass
    known_gaps:
      - helper_surface_perfection_deferred
    exit_relevance: required
    decision: closeable

  - surface_id: derived::edamage
    owner: canonical_query_engine
    contract_family: derived_v1
    consumer_scope:
      - optimizer
    maturity_label: accepted_model
    publication_status: pass
    optimizer_consumption_status: pass
    accepted_model_status: explicit
    parity_status: bounded_pass
    known_gaps:
      - helper_surface_perfection_deferred
    exit_relevance: required
    decision: closeable

  - surface_id: derived::eecon
    owner: canonical_query_engine
    contract_family: derived_v1
    consumer_scope:
      - optimizer
    maturity_label: accepted_model
    publication_status: pass
    optimizer_consumption_status: pass
    accepted_model_status: explicit
    parity_status: bounded_pass
    known_gaps:
      - broader_economy_expansion_deferred
    exit_relevance: required
    decision: closeable

  - surface_id: derived::economy.income.*
    owner: canonical_query_engine
    contract_family: derived_v1
    consumer_scope:
      - optimizer_optional_inputs
    maturity_label: bounded_contract
    publication_status: pass
    optimizer_consumption_status: pass
    accepted_model_status: explicit_boundary_only
    parity_status: not_applicable
    known_gaps:
      - unsupported_resources_explicitly_fail_closed
      - manual_externalized_inputs_not_exhaustively_modeled
    exit_relevance: required_boundary
    decision: closeable
```

## Verification evidence
- Targeted Phase 3 contract tests passed.
- Targeted Phase 3 optimizer integration tests passed.
- Targeted Phase 3 runtime publication validation passed.
- `python run_stats.py` succeeded with the landed Phase 3 publication hook enabled.
- No required Phase 3 surface is recorded as missing from the governed publication or optimizer consumption path.

## Exit decision
`complete`

## Current status
- Phase 3 implementation is substantially landed.
- Closeout certification, control-stack reconciliation, bounded evidence recording, and explicit exit decision are now recorded here.
- Full-suite legacy test cleanup is not part of this tranche and does not block the Phase 3 exit decision.
