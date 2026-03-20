# Start Here for AI

This package is the current **Tower KB + calculator baseline**.

It is suitable for:
- knowledge-base lookup
- stat compilation and stat resolution
- perk timeline generation/consumption
- progression-engine foundation work
- downstream optimizer consumption
- merge/audit/handover work

It is **not** safe to describe as:
- final full-game exact simulator truth
- final scenario-closed runtime truth
- exact tick-order canon beyond explicit package boundaries

## First-pass entry order
1. `manifest.json`
2. `readme.md`
3. `MASTER_SURFACE_TRUST_LEDGER.csv`
4. `SURFACE_PRIORITY_REGISTRY.csv`
5. `UNKNOWNS_OPERATING_POLICY.csv`
6. `MERGE_NOTES_FOR_AI.md`
7. `docs/15_engine_readiness_audit.md`
8. `docs/16_progression_engine_scope_and_burndown.md`
9. `kb/index.md`

## Canonical rebuild path
- `python run_stats.py`

## Canonical shipped output bundle
- `out/`

## Current package truth posture
- KB and calculator baseline: yes
- Progression foundation merged: yes
- Scenario runtime closure complete: no
- Optimizer exists downstream: yes
- Publish gate currently fully publishable: no, see `out/diagnostics.json`

## Pre-merge warning
Treat this package as a **truth-anchored baseline with explicit open items**, not as a completed final simulator. Preserve honest scope labels during merges.
