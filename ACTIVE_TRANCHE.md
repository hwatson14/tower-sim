# ACTIVE_TRANCHE

## Tranche ID
`PH2-TRANCHE-A_STAT_INPUT_COMPILER_FUNCTION_LEVEL_OWNERSHIP_LEDGER`

## Phase
`Phase 2 — Query Engine ownership completion`

## Objective
Classify every meaningful unit in `compilers/stat_input_compiler.py` by owner and action so the approved Query Engine seam can move without guessing or broad rewrite.

## Scope in
- `compilers/stat_input_compiler.py`
- function-level ownership mapping needed to separate Inputs-owned compilation from Query Engine-owned routing/query preparation
- destination mapping for every candidate move, split, or temporary stay
- regression anchors and test hooks needed before seam extraction

## Scope out
- direct code edits beyond minimal ledger-hosting scaffolding if needed
- formula rewrites
- opportunistic cleanup
- unrelated engine refactors
- Phase 2B seam extraction work

## Required outputs
- one function-level ownership ledger for `stat_input_compiler.py`
- explicit owner/action classification for every meaningful unit
- destination module mapping for every move or split
- regression/test anchors for risky ownership changes

## Required verification
- no major unit remains unclassified
- every move or split has a destination
- risky moves identify regression anchors
- the tranche does not imply seam extraction happened early

## Acceptance criteria
- every meaningful unit in `stat_input_compiler.py` is classified by owner and action
- every move/split row names a target module
- no code-first seam extraction happens before the ledger exists
- the tranche leaves the compiler/query boundary less ambiguous than it found it

## Blockers
- none

## Stop conditions
Stop once the ownership ledger is complete enough to govern Phase 2B extraction without guessing about unit ownership or destination surfaces.

## Non-goals
- do not rewrite formulas
- do not move code in this tranche
- do not redesign the `StatInput` schema
- do not begin undeclared family expansion
