# Canonical File Map

## Start here
- `START_HERE_FOR_AI.md`
- `AI_PICKUP_GUIDE.md`

## Core execution entrypoints
- `run_stats.py` — main build / publish entrypoint
- `parsers/ids_parser.py` — IDS ingestion
- `compilers/account_state_compiler.py` — account-state compilation
- `compilers/stat_input_compiler.py` — stat-input compilation
- `engine/stat_engine.py` — stat resolution / runtime family logic

## Core model files
- `models/account_state.py`
- `models/stat_input.py`
- `models/statbook.py`

## Canonical governance / KB files
- `config/destination_formula_ledger.yaml` — formula-family governance
- `config/stage_rules.yaml`
- `config/aliases.yaml`
- `kb/index.md`
- `KB_TARGET_STANDARD.md`
- `SURFACE_EXECUTION_ORDER.yaml`
- `TASK_ENTRYPOINTS.yaml`

## Canonical input files
- `input/_IDS.csv`
- `input/loadout.json`
- `input/perks.json`
- `input/perks_projected_max.json`
- `input/EP_Export.csv`
- `Copy of Effective Paths v5.03.02.xlsx`

## Canonical outputs
- `out/statbook.json`
- `out/statbook_publishable.json`
- `out/stat_inputs.json`
- `out/account_state.json`
- `out/diagnostics.json`
- `out/line_by_line_verification.json`
- `out/ep_oracle_compare.json`

## Canonical audit artifacts
- `FINAL_AUDIT_SUMMARY.md`
- `FINAL_AUDIT_SUMMARY.json`
- `FINAL_PRE_HANDOVER_AUDIT.md`
- `FINAL_ALL_CALCULATED_STATS.csv`
- `FINAL_ALL_CALCULATED_STATS.json`
- `FINAL_SANITY_ISSUES.json`


## Scoped active subsystem: geometry measurement-fit path
- `engine/geometry_wall_contact_target_surface.py` — canonical proxy target surface for geometry wall-contact fitting
- `engine/geometry_wall_contact_measurement_protocol.py` — measurement protocol and expected capture shape
- `engine/geometry_wall_contact_fit_ingestion.py` — ingestion for fit-ready geometry measurements
- `engine/geometry_wall_contact_fit_harness.py` — fit harness for candidate models
- `engine/geometry_wall_contact_holdout.py` — holdout partitioning for review
- `engine/geometry_wall_contact_fit_review.py` — review/reporting layer for fit results
- `engine/geometry_wall_contact_fit_decision.py` — decision layer for promotion-blocked selection
- `engine/geometry_wall_contact_artifact_harmonizer.py` — artifact harmonization for geometry fit outputs
- `engine/geometry_wall_contact_fit_pipeline.py` — narrow orchestration path for the scoped geometry tranche
- `tests/test_geometry_wall_contact_target_surface.py`
- `tests/test_geometry_wall_contact_fit_ingestion.py`
- `tests/test_geometry_wall_contact_fit_harness.py`
- `tests/test_geometry_wall_contact_holdout.py`
- `tests/test_geometry_wall_contact_fit_review.py`
- `tests/test_geometry_wall_contact_fit_decision.py`
- `tests/test_geometry_wall_contact_fit_pipeline.py`

## Test files
- `tests/test_smoke.py`
- `tests/test_perk_scaling.py`

## Scoped active subsystem: R86 pre-Codex stat-query contract pack
- `governance/R86_PRE_CODEX_FREEZE_PACK_TIGHTENING.md` — freeze/tightening note for the pre-Codex contract pack
- `governance/R86_IMPLEMENTATION_SCOPE_AND_ACCEPTANCE.md` — bounded scope and acceptance criteria for the stat-query tranche
- `governance/R86_CODEX_HANDOFF_GUARDRAILS.md` — Codex operating guardrails for the tranche
- `governance/R86_WORKED_EXAMPLES.md` — worked examples for scenario/query/state contract interpretation
- `governance/ITERATION_R86_BURNDOWN.csv` — tranche burndown tracker
- `config/stat_query_codex_work_packages.csv` — bounded Codex work-package list for stat-query implementation
- `kb/global-rules/contracts/stat-query-api-contract.yaml` — phase-1 stat-query API contract
- `kb/global-rules/contracts/stat-query-state-identity.yaml` — state identity contract
- `kb/global-rules/contracts/stat-query-scenario-families.yaml` — scenario-family contract
- `kb/global-rules/contracts/stat-query-initial-surface-set.yaml` — initial surfaced stat-query outputs
- `kb/global-rules/contracts/stat-query-surface-ownership-ledger.yaml` — surface ownership ledger for the tranche
- `kb/global-rules/contracts/baseline-contributor-map-schema.yaml` — baseline contributor map schema
- `kb/global-rules/contracts/overlay-delta-schema.yaml` — overlay delta schema
