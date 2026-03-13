# Static Pipeline V2 Phase A Locked Implementation Plan (Master-Spec Reconciled)

## 0) Lock status
- **Status:** Locked.
- **Phase:** A only (master-spec + registries + contract scaffolding + checks).
- **Authority:** `CONTRACT.md` first, then `docs/v2/TOWERSIM_V2_MASTER_SPEC.md` and handover artifacts.
- **Scope control:** No Phase B+ behavior work in this change.

## 1) Why this replacement is required
The prior provisional Phase A scaffold is non-authoritative because it introduced semantics not yet registry-grounded by the master spec (notably fabricated stage-local contributor identifiers). This replacement plan reconciles all Phase A surfaces to the supplied master spec and explicitly marks unresolved implementation layers as provisional.

## 2) Repo-path decision and governance adjustment
User instruction requires `docs/v2/TOWERSIM_V2_MASTER_SPEC.md`. Repository governance previously discouraged `/docs` by default. Because this is an explicit user requirement for a new authoritative V2 contract artifact, this plan allows `/docs` and updates `REPO_MAP.yaml` enforcement accordingly.

## 3) Concrete file mapping (Phase A)
### 3.1 Authoritative spec artifact
- Create `docs/v2/TOWERSIM_V2_MASTER_SPEC.md` with the provided content exactly.

### 3.2 Machine-readable V2 registries (first set)
- Create `tables/meta/registry/v2/target_stats.yaml`.
- Create `tables/meta/registry/v2/contributors.yaml`.
- Create `tables/meta/registry/v2/aliases.yaml` (legacy -> canonical only).
- Create `tables/meta/registry/v2/stages.yaml`.
- Create `tables/meta/registry/v2/runtime_domains.yaml` (runtime/static deny-list and domains).

### 3.3 Reconciled Phase A code surfaces
- Replace `tower_sim/registry/static_v2_contract.py` with registry-backed contract checks only.
- Replace `tower_sim/engines/static_pipeline_v2.py` with Phase A stage/materialization and registry-guard scaffolding only (no authoritative resolver semantics yet).

### 3.4 Reconciled tests
- Replace `tests/test_static_pipeline_v2.py` to enforce:
  1. canonical vs legacy alias direction,
  2. runtime/static separation,
  3. required stage presence (including `baseline_gem_respec`),
  4. prohibition of fabricated canonical contributor IDs.

### 3.5 Governance enforcement update
- Update `REPO_MAP.yaml` to allow `docs/` root subtree and markdown content under `docs/**`.

## 4) Explicit non-goals (Phase A)
- No full source-state normalization by family.
- No full contributor emission implementation for all families.
- No static target resolver implementation for all stats.
- No evaluator migration.
- No runtime overlay migration.

## 5) Provisional/non-authoritative markers
The following remain provisional in Phase A even after reconciliation:
- `tower_sim/engines/static_pipeline_v2.py` behavior beyond stage contract and adapter seam shape.
- Any legacy-to-canonical contributor mapping gaps not encoded as canonical registry rows.

## 6) Acceptance criteria for this PR
1. Master spec exists at required path and is committed.
2. V2 registries are machine-readable and loadable.
3. Alias registry direction is enforced one-way (legacy -> canonical only).
4. Runtime fields are rejected from static target acceptance.
5. Required stages include `baseline_account`, `baseline_gem_respec`, `baseline_loadout`.
6. Canonical contributor registry rejects fabricated IDs such as `legacy_stage__...`.
7. Repo map checks pass after governance update.


### 3.6 Phase A completion hardening (this pass)
- Add `tables/meta/registry/v2/source_state_schema.yaml`.
- Add `tables/meta/registry/v2/contributor_operations.yaml`.
- Add `tables/meta/registry/v2/composite_dependencies.yaml`.
- Add `tables/meta/registry/v2/quarantine_registry.yaml`.
- Add `audit/static_pipeline_v2_phase_a_coverage_audit.md` with full-domain coverage accounting and explicit Phase A readiness verdict.
