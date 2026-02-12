> **Role:** Normative migration plan for canonical stat-pipeline unification.

# Canonical Stat Pipeline Refactor Plan

## Objective

Refactor TowerSim so all runtime stat computation follows one canonical pipeline with no parallel stat-assembly paths:

1. `_IDS.csv` ingest -> typed `AccountSnapshot`
2. **Base stats stage** (account-only state)
3. **Start-of-run stage** (actual run state with loadout)
4. **At-wave stage** (wave progression + tier/BC/heat application)
5. Evaluators consume canonical stage outputs only

This preserves the frozen composition order in `ARCHITECTURE.md` and removes bypasses that can silently omit stats.

## Scope guardrails

- Deterministic only.
- No mechanics changes in this migration unless already sourced from existing authoritative repo tables/libraries.
- Fail closed when required stage inputs are missing.
- Every stage output must carry provenance and level/value lineage.
- No parallel runtime stat-assembly paths outside canonical orchestrator entrypoints.

## Canonical taxonomy (required)

To avoid category drift, all runtime outputs must use this taxonomy:

- **StatValue**: canonical stat ID + numeric value used for game/evaluator logic.
- **DerivedMetric**: diagnostic/computed metric not part of canonical stat IDs (e.g. parity deltas, debug aggregates).
- **WaveState**: wave-indexed state tuple (`W_actual`, `W_attack`, `W_health`) used for at-wave transforms.

Rule: evaluators may consume `StatValue` and `WaveState`; `DerivedMetric` is never allowed to masquerade as a canonical stat.

## Stage membership table (authoritative for migration)

This table defines the first stage where each contributor class appears. Any disagreement must be resolved here before implementation.

| Contributor class | Stage 1 Base (account-only) | Stage 2 Start-of-run (loadout/actual run state) | Stage 3 At-wave (wave/tier transforms) | Notes |
| --- | --- | --- | --- | --- |
| Workshop coin levels (start state) | ✅ | carry | carry | Base account state source for many canonical stats. |
| Labs | ✅ | carry | carry | Persistent account progression. |
| Relics / permanent account bonuses | ✅ | carry | carry | Persistent multipliers/deltas. |
| UW unlocked tracks + baseline values | ✅ | carry | carry | Account-owned baseline UW state. |
| Modules (equipped preset) | ❌ | ✅ | carry | Loadout-time contributor only. |
| Cards (equipped preset) | ❌ | ✅ | carry | Loadout-time contributor only. |
| Bots / Guardians (active preset state) | ❌ | ✅ | carry | Loadout-time contributor only. |
| Perk timeline effects | ❌ | optional carry-in if deterministic timeline at run start | ✅ | Applied by explicit deterministic timeline artifact by wave. |
| Tier battle conditions | ❌ | ❌ | ✅ | Applied in frozen order at wave stage. |
| Tournament heat modifiers | ❌ | ❌ | ✅ | Applied in frozen order at wave stage. |
| Wave progression (free upgrades, EALS/EHLS ramp, wave mapping) | ❌ | ❌ | ✅ | Depends on wave index and run context. |

## Canonical stage contracts

### Stage 0 — Snapshot ingest contract

Input: `_IDS.csv`.
Output: validated `AccountSnapshot`.

Requirements:
- Naming contract validation required.
- Missing required account sections fail closed.

### Stage 1 — Base stats contract (account-only)

Output: `BaseStatStage` with:
- canonical `StatValue` map
- source contributor records
- source level + resolved value per contributor (when level-driven)
- deterministic provenance tags

Rules:
- No loadout application at this stage.
- No wave/tier/battle-condition application at this stage.

### Stage 2 — Start-of-run contract (actual run state)

Output: `StartOfRunStage` with:
- merged values from Stage 1 + loadout contributors
- preserved contributor lineage (including source levels)
- explicit merge policy metadata

Rules:
- Loadout-aware by scenario preset/mode.
- Must not recompute Stage 1 from raw IDS independently.

### Stage 3 — At-wave contract

Output: `AtWaveStage` with:
- canonical `StatValue` map keyed by canonical stat IDs
- `WaveState` (`W_actual`, `W_attack`, `W_health`)
- applied tier rules/BC/heat ledger

Rules:
- No direct base/loadout recompilation.
- Must derive from Stage 2 + explicit wave/tier inputs.

## Canonical orchestrator contract (single runtime entrypoint)

All runtime consumers must use this API shape (or a fully equivalent typed interface):

```python
build_canonical_stat_pipeline(
    *,
    snapshot: AccountSnapshot,
    scenario: ScenarioSpec,
    preset: str | None,
    wave: int | None,
    include_perk_timeline: bool,
) -> CanonicalPipelineResult
```

`CanonicalPipelineResult` must include:
- `base_stage`
- `start_stage`
- `at_wave_stage` (when `wave` is provided)
- `diagnostics` (`DerivedMetric` bucket)
- `missing` (fail-closed markers)

Determinism/caching contract:
- Pure function semantics for identical inputs.
- If memoized, cache key must be deterministic over snapshot identity + scenario + preset + wave + perk timeline config.

## Migration strategy

### Variant selection

Adopt **Variant 1 (consumer-first wedge)**:
1. Route `MAX_WAVE` runtime path through canonical orchestrator first.
2. Add golden-stage anchors for MAX_WAVE-required stats.
3. Then converge remaining runtime consumers.

Rationale: current pain is wrong evaluator outcomes, so consumer correctness is prioritized over broad internal cleanup.

## Migration phases

### Phase A — Contract-first scaffolding (time-boxed)

- Introduce stage dataclasses + orchestrator API.
- Internally permit legacy compiler reuse, but only behind orchestrator boundary.
- Emit stage diagnostics for parity checks.

**Exit criteria (must all pass before Phase B):**
- Orchestrator API exists and is the only new runtime stat entrypoint.
- Golden stats fixture tests added and passing for one pinned snapshot.
- Guardrail ratchet blocks new direct runtime bypass callsites.

### Phase B — Consumer convergence

- Route runtime consumers through canonical orchestrator:
  - `MAX_WAVE` evaluator path (first)
  - run API stat tasks
  - diagnostics/statbook writers used for runtime decisions
- Remove direct runtime use of low-level compilers outside orchestrator.

**Exit criteria:**
- Runtime consumers listed above call orchestrator only.
- Required-stat completeness checks pass at stage boundaries.

### Phase C — Bypass removal + strict enforcement

- Remove or hard-gate legacy direct runtime callsites.
- Promote guardrail from ratchet mode (no new bypasses) to strict mode (single runtime entrypoint only).

**Exit criteria:**
- Allowlist reduced to orchestrator-only approved callsites.
- CI fails on any direct low-level runtime compiler call outside orchestrator.

## Tests and enforcement requirements

## 1) Stage parity tests

Add fixtures validating stage outputs for pinned snapshot inputs:
- Stage 1 contains account-only contributors.
- Stage 2 differs from Stage 1 only by loadout/start-of-run contributors.
- Stage 3 differs from Stage 2 only by wave/tier transforms.

## 2) Golden stats fixture tests (external anchor)

Add a pinned deterministic “golden stats” fixture (at least one snapshot/preset) with ~10 high-leverage canonical stats, asserted across stages (where applicable). Candidate set:
- `tower_hp`
- `tower_regen`
- `def_pct`
- `eals_pct`
- `ehls_pct`
- `tower_attack_speed`
- `tower_crit_chance`
- `tower_crit_multiplier`
- `wall_hp`
- one UW cooldown or equivalent canonical UW stat

Rule: values must be computed from authoritative repo tables/libraries and checked exactly or with explicit tolerance policy.

## 3) Level/value lineage tests

For level-driven contributors:
- level exists
- resolved value exists
- recomputation from level/table/formula matches within tolerance

For non-level contributors:
- level field must be null/absent

## 4) Required-stat completeness tests

Per evaluator contract, ensure all required canonical stat IDs are present at required stage boundaries.
Missing required IDs fail closed.

## 5) No-bypass guardrails

- Add static callsite guardrails over runtime Python modules.
- Ratchet rule: no *new* direct calls to low-level stat compilers outside allowlist.
- Strict rule (Phase C): only orchestrator callsites permitted.

## 6) CI gates

Pipeline checks must run in CI:
- unit tests for guardrail collector
- repository guardrail assertion
- stage-contract tests for pinned fixture snapshot
- golden stats fixture tests

## Completion criteria

Refactor is complete when:
- All runtime stat consumers use canonical orchestrator stages.
- No runtime bypass callsites remain outside declared orchestrator flow.
- Stage contracts enforce level/value lineage.
- Required stat completeness is fail-closed and covered by tests.
- Golden stats fixtures are green for pinned snapshots.
