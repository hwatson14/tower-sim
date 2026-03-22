# ACTIVE_TRANCHE

## Tranche ID
`PH2-TRANCHE-B_COMPILER_QUERY_SEAM_EXTRACTION`

## Phase
`Phase 2 — Query Engine ownership completion`

## Objective
Extract only the approved Query Engine-owned seam from `compilers/stat_input_compiler.py` into canonical owner surfaces, using the completed Phase 2A ownership ledger as the governing boundary.

## Scope in
- approved Query Engine-owned logic identified in `docs/phase2a_stat_input_compiler_ownership_ledger.md`
- `compilers/stat_input_compiler.py` compatibility-entrypoint preservation
- owner-correct extraction into Query Engine surfaces
- targeted regression coverage and boundary rationale updates for moved logic

## Scope out
- formula rewrites
- `StatInput` schema redesign
- generic helper-sink creation
- opportunistic cleanup unrelated to the approved seam
- undeclared family expansion beyond the ledger-governed moves

## Required outputs
- extracted owner-correct code changes for the approved seam
- updated boundary rationale for the compiler/query split
- updated targeted regression coverage for the moved behavior

## Required verification
- runtime behavior remains stable for the compatibility entrypoint
- moved behavior is covered by targeted tests
- docs and tranche state reflect the new boundary truth

## Acceptance criteria
- only ledger-approved Query Engine-owned units move
- `compilers/stat_input_compiler.py` remains a valid compatibility entrypoint
- targeted regressions cover moved behavior
- the compiler/query boundary is less owner-ambiguous than before extraction

## Blockers
- none

## Stop conditions
Stop once the approved seam is extracted, compatibility behavior is preserved, and targeted regression evidence is landed.

## Non-goals
- do not rewrite formulas
- do not redesign `StatInput`
- do not move undeclared Inputs-owned compilation logic
- do not begin Phase 2C delegation-manifest work inside this tranche
