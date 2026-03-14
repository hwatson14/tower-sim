# Decision Log

## 2026-03-14
### Decision
Treat **v2** as the only active architecture target.

### Reason
The repo already defines the correct layered architecture under v2. Creating v3 now would duplicate aspiration rather than reduce ambiguity.

### Consequence
Do not create v3 namespaces, folders, or parallel active implementations.

---

## 2026-03-14
### Decision
Move the KB into the repo as a first-class subtree.

### Reason
Keeping KB and repo separate created split-brain architecture, slower implementation, and manual context transport.

### Consequence
`kb/` is now part of the active codebase and should be treated as the authoritative reference core.

---

## 2026-03-14
### Decision
Keep executable IDS ingestion in active repo code paths rather than inside `kb/`.

### Reason
Parser/compiler are executable ingestion logic, not reference knowledge.

### Consequence
Ingestion remains in repo-native implementation surfaces, while KB holds contracts, formulas, routing, and reference truth.

---

## 2026-03-14
### Decision
Use bounded Codex phases rather than broad “rebuild the sim” prompts.

### Reason
Codex is stronger at constrained implementation than ambiguous architectural interpretation.

### Consequence
Work proceeds by narrow architecture phases with explicit acceptance criteria.

---

## 2026-03-14
### Decision
Import KB by artifact class in slices rather than a single giant diff.

### Reason
Full import exceeded practical diff size and created unnecessary failure risk.

### Consequence
KB import was split into:
1. contracts/indexes/registries
2. tables/formulas/ledgers
3. validation-facing surfaces and cleanup

---

## 2026-03-14
### Decision
Allow kebab-case filenames under `kb/` only.

### Reason
The imported KB’s canonical filenames are kebab-case, while the repo should remain strict elsewhere.

### Consequence
Filename governance remains strict repo-wide except for the scoped `kb/` subtree exception.

---

## 2026-03-14
### Decision
Extend existing repo-native bridge surfaces rather than create a parallel stage contract system.

### Reason
The repo already had the natural contract home in `tables/meta/registry/v2/stages.yaml` and `static_v2_contract.py`.

### Consequence
Stage bridge governance now lives inside native v2 contract surfaces.

---

## 2026-03-14
### Decision
Materialize static staged outputs before attempting runtime overlays.

### Reason
Static stages are the necessary foundation for clean runtime separation.

### Consequence
`baseline_account`, `baseline_gem_respec`, and `baseline_loadout` are now the stable pre-runtime substrate.

---

## 2026-03-14
### Decision
Tighten contributor-family routing before starting runtime overlay work.

### Reason
Runtime work should not depend on loose provenance-prefix heuristics.

### Consequence
`StatInput` now carries explicit contributor-family metadata at staged materialization, with fail-closed validation.
