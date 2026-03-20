# Static Pipeline V2 Phase A Semantic Audit

## Scope reviewed
- `docs/v2/TOWERSIM_V2_MASTER_SPEC.md`
- `tables/meta/registry/v2/*.yaml`
- `tower_sim/registry/static_v2_contract.py`
- `audit/static_pipeline_v2_phase_a_coverage_audit.md`

## Semantic checks and outcomes

### 1) Canonical contributor row semantics
- Check: each canonical contributor entry maps one contributor id to one owned target stat and one operation class.
- Outcome: pass for canonical rows after schema hardening (`owned_target_stat`, `operation_class`, `stage_applicability`, `ownership_role`, `canonical_status`, `migration_status` required).

### 2) Owned target and operation backing
- Check: contributor `owned_target_stat` must be in canonical target registry; `operation_class` must be in operation registry.
- Outcome: pass by contract enforcement in `static_v2_contract`.

### 3) Stage applicability plausibility
- Check: stage applicability must not be silently broad; unresolved families should be explicit exceptions.
- Outcome: pass with explicit quarantine for unresolved stage families (`perk`, `battle_condition`, `guardian`) rather than canonical overreach.

### 4) Alias direction
- Check: aliases must be legacy -> canonical only, never canonical -> legacy.
- Outcome: pass with fail-closed enforcement.

### 5) Quarantine quality
- Check: quarantine must be explicit, enumerable, and not a hidden catch-all.
- Outcome: pass; quarantined contributors are enumerated with reason codes and ownership metadata.

### 6) Composite dependency sufficiency
- Check: composite/dependent targets must be explicitly classified as defined or deferred-blocked.
- Outcome: pass for Phase A entry criteria; registry classifies discovered composite targets and marks unresolved dependency-token gaps as deferred-blocked.

### 7) Full-domain accounting
- Check: all discovered static items must end as canonical, alias, quarantine, or blocked/unresolved.
- Outcome: pass on coverage accounting (`uncovered_items` empty for targets and contributors).

## Semantic risk notes
- Blocked legacy/repo-surface names remain high and require deterministic canonicalization policy in Phase B/C.
- Quarantined contributor families and medium-confidence rows remain explicit migration work.

## Verdict
**Phase A semantic gate: PASS (with explicit blocked/quarantine backlog), safe to begin Phase B source-state normalization.**
