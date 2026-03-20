# Open Gaps

## Current blocking gap
### Combat/runtime-state execution
- **Severity:** High
- **Blocking:** Yes
- **Owner:** Current implementation phase
- **Target phase:** Post-overlay runtime work
- **Description:** Runtime overlays are now materialized as a governed layer, but combat state, boss state, and runtime-state execution semantics are still intentionally unimplemented.

### Why this matters
Without runtime-state execution semantics on top of governed overlays, the repo cannot yet deliver end-to-end runtime behavior or evaluator integration.

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
