# v3 Bootstrap Plan

This folder is an isolated rebuild track for TowerSim v3.

## Seed artifact
- Source KB zip: `../tower_kb_frozen_regenerated.zip`
- Canonical knowledge source for v3 rebuild work: `tower_kb_frozen_regenerated.zip`
- Required KB source for v3 runtime work: extracted KB tree at `kb/` (single canonical working tree).

## Guardrails
- Do not seed v3 from alternate KB snapshots unless explicitly re-approved; `tower_kb_frozen_regenerated.zip` is canonical for this track.
- Keep active v2 runtime (`tower_sim/`) untouched unless explicitly requested.
- Build v3 as a separate codebase with its own composition root under `v3/`.
- Preserve deterministic, fail-closed behavior and explicit provenance for all mechanics.

## Initial next steps
1. Unpack the KB artifact into a bounded reference subtree in `v3/`.
2. Define a minimal v3 contract + repo map local to `v3/`.
3. Implement the smallest deterministic core first (`MAX_WAVE` parity target).
4. Add explicit verification fixtures before broader feature porting.

## Reviewed next steps after KB scan (v3 stats expansion)

The current KB is package-complete for intended simulator scope, with canonical
mechanics in `kb/**/tables/**`, runtime semantics in `kb/**/contracts/**`, and
explicit boundary-policy files that must be honored fail-closed.

### 1) Stabilize v3 KB access + contract lock layer
- Implement `v3.kb_access` as the single accessor for extracted `kb/` content,
  including deterministic path resolution and SHA-256 helpers.
- Add/restore `v3/kb_contract_lock.yaml` and lock at least:
  - `kb/global-rules/contracts/naming-contract.yaml`
  - `kb/global-rules/contracts/ids-section-routing.yaml`
- Keep strict drift checks via `scripts/generate_kb_drift_report.py`.

### 2) Complete IDS→snapshot→stat-input v3 composition root
- Keep reusing existing deterministic parser/compiler surfaces short-term, but
  wire them through one v3 entrypoint module so v3 has one composition root.
- Require v3 calls to pass through:
  1. IDS parse
  2. account snapshot compile
  3. stat input compile + naming-contract validation

### 3) Close contributor-family coverage in stat-input validation
- Expand provenance-to-family mapping only from KB-authorized contributor
  sections (no invented families).
- Add explicit fail-closed errors for ambiguous provenance prefixes.
- Add fixture assertions that every emitted v3 `StatInput` has:
  - registry-known `stat_id`
  - non-empty provenance
  - KB-allowed contributor family.

### 4) Implement KB-driven stat family loaders (account input registries first)
- Prioritize input-registry families called out by KB target standard:
  `relic`, `player_stuff`, `theme_song`, `unlock`, externalized `vault`.
- For each family, land deterministic loader + normalization + provenance
  tagging before adding downstream mechanics.

### 5) Stage mechanics activation from manifest-governed surfaces
- For each domain in this order: `workshop`, `labs`, `cards`, `modules`,
  `ultimate-weapons`, `bots`, `perks`, `combat`, `enemies`:
  - map required canonical tables/contracts
  - implement deterministic transforms
  - gate with contract tests before enabling next domain.

### 6) Add closure-gate tests aligned to KB control plane
- Add tests that fail if v3 runtime reads from `notes/`, `sources/`, or
  `derived/` as mechanics authority.
- Add checks for boundary handling (`accepted_unknown_boundary`, out-of-scope
  same-tick precedence) to ensure explicit stop behavior.
- Keep `check_repo_map`, naming-contract checks, and KB drift report in the
  default v3 validation path.

### 7) Define first executable v3 objective milestone
- Milestone A: deterministic statbook completeness across all account input
  families with lineage/provenance output.
- Milestone B: `MAX_WAVE` parity slice using shared common core.
- Milestone C: selective expansion to additional objectives only after A/B are
  green and contract-locked.


## Implementation status (current)
- Step 4: completed with `v3/account_input_registry.py` KB-driven deterministic loaders for `relic`, `player_stuff`, `theme_song`, `unlock`, and externalized `vault` registries.
- Step 5: completed with `v3/mechanics_activation.py` manifest-gated ordered domain activation plan and canonical-surface validation.
- Step 6: completed with closure-gate enforcement (`v3.kb_access.read_csv_rows(..., authority="mechanics")`) plus boundary-policy fail-closed checks in `v3/boundary_policy.py`.
- Step 7: completed with executable milestone evaluator in `v3/milestones.py` and fixture-backed tests for milestone A/B/C status outputs.


## Full closure plan (KB-accurate + v3-only)

### Scope targets
- **Scope 1 (KB-accurate canonical stat pipeline):** all canonical stat inputs are validated against KB routing contracts with explicit fail-closed behavior and no unknown contributor families.
- **Scope 2 (v3-only runtime boundary):** runtime tasks consume v3 composition root only; legacy runtime paths are either replaced or explicitly fail-closed.

### Phase 1 — Canonical stat closure hardening (current + final gaps)
1. Keep `v3/stat_input_compiler.py` as the single canonical stat-input gate with:
   - contract-lock hash checks,
   - naming-contract validation,
   - source-family validation from `ids-section-routing.yaml`,
   - canonical route validation from `contributor-mappings-full.yaml`.
2. Maintain explicit buckets for diagnostics:
   - `dropped_noncanonical` for sanctioned noncanonical surfaces,
   - `dropped_kb_unwired` for known families missing canonical routes,
   - hard error for unknown families/provenance.
3. Add/maintain tests proving:
   - unknown families fail closed,
   - known noncanonical families are dropped (not silently accepted),
   - known families without canonical rows report as `kb_unwired`.

### Phase 2 — Noncanonical surface closure against KB contracts
1. Enumerate noncanonical stat surfaces emitted by current compiler and map each to KB destination class in `ids-section-routing.yaml`.
2. Replace implicit compatibility exceptions with explicit KB-backed checks per family/prefix.
3. Add a deterministic report gate that fails if a noncanonical row appears from a canonical-only family.

### Phase 3 — v3-only runtime closure
1. Keep `BASE_STATS` and `STAT_INPUTS` on v3 composition path.
2. Keep `MAX_WAVE` fail-closed until v3-native max-wave composition is implemented.
3. Implement v3-native max-wave evaluation path that consumes:
   - v3 stage composition outputs,
   - shared deterministic simulation core,
   - no legacy composition assembly.
4. Switch `MAX_WAVE` from fail-closed placeholder to v3-native implementation only after parity fixtures are green.

### Phase 4 — Closure gates and release criteria
A change is closure-complete only when all are true:
- `python scripts/v3_stat_contribution_diagnostic.py ...` reports:
  - `missing_systems == 0`,
  - `routing_gaps == 0`,
  - `dropped_kb_unwired.count == 0`,
  - dependency summary `not_ok == 0`.
- `pytest` coverage for v3 compiler/pipeline/engine/API gates is green.
- KB contract lock includes naming, ids-section routing, and contributor routing contracts.
- Runtime tasks in scope execute via v3-only paths or explicit fail-closed placeholders.

### Explicit out-of-scope until requested
- Expanding mechanics formulas beyond current KB-authorized canonical/contract surfaces.
- Optimizer behavior changes unrelated to v3 composition closure.
