# R86 Codex handoff guardrails

## Hard rules
1. Do not create a parallel scenario contract stack.
2. Do not create a second truth-owning stat engine.
3. Do not pre-materialise full resolved statbooks.
4. Do not broaden beyond `timing_v1` and `progression_v1` in phase 1.
5. Do not migrate geometry in phase 1.
6. Do not migrate broad combat-helper ownership in phase 1.
7. Do not hide state identity or scenario assertions in globals.
8. Do not add undocumented formulas.
9. Do not let downstream consumers re-derive surfaces owned by the canonical query engine.

## Steering rules
- Prefer editing existing files and seams where the repo already has an architectural foothold.
- New files are allowed only when they match the contracts in this pack and are justified in code comments or merge notes.
- Runtime/state contracts remain owned by the existing repo contracts; stat-query contracts extend them.
- Baseline materialiser phase 1 must normalize compiler output rows rather than replace compiler semantics.

## Allowed new implementation domains in phase 1
- state identity binding helpers
- bounded family baseline materialiser
- overlay applicator
- query API kernel
- timing_v1 migration
- progression_v1 migration

## Required worked examples to preserve in code/tests
- one baseline contributor-map example
- one overlay delta example
- one resolved query response example
