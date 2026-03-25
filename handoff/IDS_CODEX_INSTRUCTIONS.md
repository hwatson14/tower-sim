# Codex Handoff Instructions

This bundle is intended to be added to repo root and used as the control plane for Codex work.

## Primary documents

1. `IDS_EXECUTION_CONTROL_REGISTER.md`
   - tranche ordering
   - dependencies
   - execution status
   - acceptance artifacts
   - merge gates

2. `IDS_TRANCHE_CONTRACTS.md`
   - tranche-by-tranche implementation contracts

3. `ids_pipeline_normalized_master_register.md`
   - root-cause normalized bug register

4. `ids_pipeline_bug_ledger_v19.md`
   - raw evidence appendix

## How Codex should work

1. Read `IDS_EXECUTION_CONTROL_REGISTER.md` first.
2. Pick the first tranche whose hard dependencies are closed and whose execution status is Codex-ready.
3. Read the corresponding section in `IDS_TRANCHE_CONTRACTS.md`.
4. Implement only that tranche’s root-cause scope.
5. Do not patch downstream symptoms outside the tranche except where explicitly required by acceptance artifacts.
6. Regenerate only the artifacts named in the tranche acceptance criteria.
7. Update burndown state in the execution control register after each tranche attempt.

## Non-negotiable rules

- Do not create new local preset truth tables.
- Do not add more fail-open fallbacks.
- Do not serialize synthetic namespaces into canonical artifacts.
- Do not update tests first to match broken behavior.
- Do not close downstream cleanup tranches before contract tranches settle.

## Recommended working sequence

1. `TRANCHE_IDS_C1_CONTRACT_REGISTRY`
2. `TRANCHE_IDS_C5_STATE_SEMANTICS`
3. `TRANCHE_IDS_C2_RUNTIME_FIVE_PRESET`
4. `TRANCHE_IDS_C11_PERK_PRESET_CONTRACT`
5. `TRANCHE_IDS_C12_NAMESPACE_HYGIENE`
6. `TRANCHE_IDS_C10_CLEAN_SECTION_INGESTION`
7. `TRANCHE_IDS_C7_WSPLUS_TYPED_MODEL`
8. `TRANCHE_IDS_C8_UW_TYPED_TRACKS`
9. `TRANCHE_IDS_C9_BOT_TYPED_STATE`
10. `TRANCHE_IDS_C13_AUDIT_SURFACE_CONTRACTS`
11. `TRANCHE_IDS_C14_ARTIFACT_OUTPUT_CONTRACTS`
12. `TRANCHE_IDS_C15_VERIFICATION_REALIGNMENT`
13. `TRANCHE_IDS_C16_COMPLETENESS_MATRIX`

## What to commit in each tranche PR

- code changes
- tests
- regenerated named artifacts only
- brief note referencing tranche ID and acceptance artifacts
- explicit note of any unresolved dependency or blocked decision

## What not to do

- do not collapse multiple tranches into one PR unless explicitly requested
- do not refresh all fixtures opportunistically
- do not rename synthetic states in reports without fixing namespace hygiene boundary
- do not “solve” missing-state semantics by defaulting to Farming or empty values

