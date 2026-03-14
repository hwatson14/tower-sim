# Open Gaps

## Current blocking gap
### Runtime overlay foundation
- **Severity:** High
- **Blocking:** Yes
- **Owner:** Current implementation phase
- **Target phase:** Runtime overlay foundation
- **Description:** The repo has static staged outputs, but runtime overlays are not yet materialized as a governed layer.

### Required overlay families
- perks
- battle_conditions
- cash_workshop_purchases / workshop runtime progression
- free_upgrades
- eals_realized_effect
- ehls_realized_effect

### Why this matters
Without a governed runtime overlay layer, the repo cannot safely progress toward runtime-state execution or evaluator integration.

---

## Next gap after overlays
### Combat/runtime-state execution
- **Severity:** High
- **Blocking:** Future
- **Owner:** Later phase
- **Target phase:** Post-overlay runtime work
- **Description:** Combat state, boss state, and runtime-state execution are still intentionally unimplemented.

---

## Known non-blocking quality gap
### Contributor-family metadata upstream emission
- **Severity:** Medium
- **Blocking:** No
- **Owner:** Future tightening
- **Target phase:** Later static/runtime refinement
- **Description:** Contributor-family identity is now explicit at staged materialization, but not yet emitted natively from all upstream compiler/resolver sources.

### Current status
- acceptable for current architecture
- not the immediate bottleneck

---

## Known non-blocking KB gap
### KB verification remains incomplete
- **Severity:** Medium
- **Blocking:** No
- **Owner:** Ongoing KB iteration
- **Target phase:** Parallel track
- **Description:** The KB is integrated and structurally useful, but still iterating and being verified. Future KB versions should be treated as governed content refreshes, not architecture rewrites.

---

## Governance rule
A gap is blocking only if it prevents:
1. clean architectural progression, or
2. deterministic fail-closed behavior in the current target phase.

Everything else should be recorded here and deferred rather than derailing the active phase.
