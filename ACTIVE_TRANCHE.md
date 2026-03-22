# ACTIVE_TRANCHE

## Tranche ID
`PH3-TRANCHE-A_OBJECTIVE_STATE_CONTRACTS_AND_MATURITY_LEDGER`

## Phase
`Phase 3 — Objective-state promotion`

## Objective
Declare the governed contract, maturity, and contributor-trace expectations for `objective_state::ehp`, `objective_state::edamage`, and `objective_state::eecon` before per-objective promotion work begins.

## Scope in
- objective-state contract declarations for `objective_state::ehp`, `objective_state::edamage`, and `objective_state::eecon`
- maturity labels and known-gap statements for each objective surface
- contributor-trace expectation definitions that later promotion/parity tranches must satisfy
- explicit promotion handoff to the per-objective Phase 3 implementation tranches

## Scope out
- objective formula implementation changes
- optimizer rewires
- evaluator implementation
- accepted-model parity evidence beyond declaring the required surfaces and expectations

## Required outputs
- objective-state contract rows
- objective-state maturity ledger
- contributor-trace expectation rows
- explicit Phase 3 promotion handoff note

## Required verification
- all three objective states have declared query surfaces
- maturity labels and known-gap statements are explicit
- contributor-trace expectations are defined for each objective surface
- the next Phase 3 promotion tranches are unblocked without guessing

## Acceptance criteria
- `objective_state::ehp`, `objective_state::edamage`, and `objective_state::eecon` each have declared governed query surfaces
- maturity and known-gap posture is recorded per objective state
- contributor-trace expectations are explicit enough to govern later parity evidence
- follow-on per-objective promotion work can start without inventing missing contract truth

## Blockers
- none

## Stop conditions
Stop once the three objective-state surfaces, their maturity labels, and their contributor-trace expectations are all recorded in the canonical control/contract surfaces and the next Phase 3 tranches are unambiguous.

## Non-goals
- do not implement the eHP, eDamage, or eEcon formulas in this tranche
- do not rewire optimizer consumers yet
- do not record parity evidence that belongs to later Phase 3 closure work

## Folded residue conclusions

### Phase 2 closeout
- Phase 2 exit evidence is complete enough to promote the program into Phase 3 objective-state work.
- The delegated benchmark failure for `timing_tournament_no_perks` remains a visible bounded note, not a blocker that reopens the governed Phase 2 exit gate.
- Objective-state promotion is now the next active workstream, starting with declared contract and maturity truth rather than immediate formula rewrites.
