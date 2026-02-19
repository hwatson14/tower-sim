> **Role:** Authoritative normative contract for TowerSim.

# TowerSim Contract

**Precedence rule:** If any repository document conflicts with `CONTRACT.md`, `CONTRACT.md` is authoritative.

## 1) Project context and constraints
- Personal project for one user (Harry). Optimize for simplicity and maintainability over extensibility.
- Implementation is delegated to coding agents (Codex/ChatGPT). Documentation is the primary anti-drift control surface.
- Prefer the simplest viable solution; avoid unnecessary abstractions, framework churn, and indirection.
- Minimize document/file sprawl. Prefer editing existing canonical files to creating new ones.
- Fail-closed always: no invented mechanics, no guessed defaults, no hidden assumptions.
- In documentation refactors, scope is docs plus the minimum enforcement updates needed to keep checks green.

## 2) Scope and intent (v1 locked)
TowerSim is a deterministic simulator for *The Tower — Idle Tower Defense*. The v1 objective is to compute **maximum reachable wave (`MAX_WAVE` / `Wmax`)** for a fully specified scenario using explicit, auditable inputs.

### 2.1 Non-negotiable philosophy
- Deterministic outcomes.
- No silent defaults.
- No invented mechanics.
- Explicit assumptions and provenance.
- Fail-closed behavior when required data is missing, ambiguous, or unsupported.

### 2.2 What v1 includes
- Deterministic stat compilation from authoritative inputs.
- Deterministic mechanics application selected by manifest.
- Deterministic `MAX_WAVE` evaluation and auditable outputs.

### 2.3 What v1 excludes
- Economy outputs (coins/hour, cells/hour, etc.).
- Frame-by-frame combat simulation.
- Monte Carlo/sampling/RNG simulation.
- In-core perk probability simulation (perk-order variability is externalized as artifact/policy input).
- Optimizer execution (future scope).

## 3) Canonical system model
TowerSim treats `Wmax` as an envelope-intersection/root-finding problem between enemy pressure and player survivability.

### 3.1 Variability policy (strict)
Allowed bounded variability:
1. Deterministic timing-overlap envelopes (e.g., DR/CC overlap effects).
2. Perk acquisition order as externally supplied variability artifact.

All other variability sources are out-of-contract unless this document is explicitly revised.

### 3.2 Heuristic policy
Heuristics/shortcuts are prohibited unless all conditions hold:
- backed by authoritative source data,
- explicitly documented as assumption/provenance,
- deterministic and bounded,
- accepted as contract-compliant for the target scope.

Otherwise: fail closed.

## 4) Architecture contract (ownership planes)
Pipeline responsibilities are stable and deterministic:
1. Load authoritative inputs.
2. Compile deterministic stat inputs and lineage/provenance.
3. Resolve mechanics via manifest-selected packs only.
4. Evaluate objective(s) (`MAX_WAVE` in v1).
5. Emit auditable outputs and diagnostics.

Canonical ownership planes:
- `tower_sim/loaders/`: IO/parsing only.
- `tower_sim/libs/`: deterministic interpreters/reference table helpers.
- `tower_sim/engines/`: mechanics/stat engines; no hidden IO side effects.
- `tower_sim/evaluators/`: objective evaluators.
- `tower_sim/run/`: orchestration, ProblemSpec wiring, entrypoints.
- Shared support: `tower_sim/registry/`, `tower_sim/util/`, `tower_sim/audit/` (audit code only).

## 5) Source of truth hierarchy
1. Harry reference sheets (authoritative).
2. Tower wiki references (secondary; must be cited in PR notes where used).
3. Existing in-repo tables/libraries with clear provenance.

No mechanic/formula implementation without explicit source backing.

## 6) Mechanics manifest authority
- Mechanics and formula packs must be loaded through `mechanics/manifest.yaml`.
- Runtime must not bypass manifest-driven selection.
- Do not introduce alternate runtime override paths that bypass the manifest contract.
- No new mechanics packs/files unless explicitly requested.

## 7) Repository governance and structure
Top-level structure is machine-enforced by:
- `REPO_MAP.yaml`
- `scripts/check_repo_map.py`
- `tests/test_repo_map.py`

### 7.1 Structure rules
- Root doc set stays intentionally small.
- Do not create `/docs` or other new root buckets unless contract/enforcement requires it.
- Generated artifacts belong in `audit/` or `out/`.
- Generated markdown/json/yaml must not be committed under `tower_sim/`.

### 7.2 Authoritative documentation set
- `CONTRACT.md` — single normative contract.
- `AGENTS.md` — detailed agent execution rules and workflow expectations.
- `README.md` — user-facing orientation and operational navigation.
- `REPO_MAP.yaml` — machine-enforced repository contract.
- `IMPLEMENTATION_STATUS.md` — current implementation status/gap ledger.
- `TESTING.md` / `CONTRIBUTING.md` — process details.


### 7.3 Architecture diagram (draft)
- v35 architecture diagram is directional only and may be wrong/incomplete.
- Canonical files:
  - `out/contract_diagram_v35_draft/towersim_contract_diagram_v35_draft.png` (generated output path)
  - `out/contract_diagram_v35_draft/generate_contract_diagram_v35.py`
  - `out/contract_diagram_v35_draft/README.md`
- Regenerate with: `python out/contract_diagram_v35_draft/generate_contract_diagram_v35.py --out out/contract_diagram_v35_draft/towersim_contract_diagram_v35_draft.png`.
- `matplotlib` is required only to regenerate the draft PNG; it is not a TowerSim runtime dependency.
- If PR tooling cannot handle binaries, commit the generator+README and regenerate the PNG from this canonical path locally.
- Wiring changes must update diagram output and generator in the same PR.

### 7.4 Migration plans are temporary
- `STAT_PIPELINE_REFACTOR_PLAN.md` is a migration aid and non-authoritative.
- Once pipeline refactor implementation is complete, `STAT_PIPELINE_REFACTOR_PLAN.md` MUST be deleted in the same PR as the final implementation step (or immediately after).
- Precedence: `CONTRACT.md` overrides migration plans; migration plans override draft diagrams.

## 8) Required behavior for coding agents
- No scope creep: only implement requested scope.
- No silent behavior changes.
- Explain formulas, assumptions, and provenance in PRs.
- If required source data is missing/ambiguous, stop and raise explicit error.
- Prefer edit-over-create for files; justify unavoidable new files.
- Avoid drive-by refactors/reformatting unrelated code.

## 9) Pull request requirements
Every PR must include:
1. Summary of what changed and why.
2. Explicit provenance for mechanics/constants/data decisions.
3. Local verification commands and outcomes.
4. Any known limitations or deferred follow-ups.
5. Confirmation that changes stayed within scope.

## 10) Definition of done
For each PR:
- Code imports/compiles where applicable.
- Relevant tests/checks pass.
- Constants/mechanics include provenance.
- No silent changes.
- Contract/rules remain internally consistent.

## 11) Change control for this contract
Changes to `CONTRACT.md` should be infrequent and explicit. Any contract change must:
- include rationale,
- note downstream enforcement/doc updates required,
- preserve fail-closed behavior,
- avoid hidden broadening of scope.

### 11.1 Mandatory section for contract-change PRs
If a PR modifies `CONTRACT.md`, include a dedicated section titled **"Contract change impact"** with:
- rationale for the contract edit,
- affected sections and expected behavioral impact,
- enforcement/docs/tests updated to stay consistent.

## 12) Decision log (high-impact policy decisions)
- **2026-02:** Consolidated legacy authority docs into a single `CONTRACT.md` authority model.
- **2026-02:** Kept `IMPLEMENTATION_STATUS.md` separate from the contract (normative vs. status split).
- **2026-02:** Restored detailed guidance in `CONTRACT.md`, `AGENTS.md`, and `README.md` while preserving minimal doc count.

## Appendix A) Game context narrative (non-normative, explanatory only)
This appendix is explanatory context for humans and coding agents. It is **not** a source of new mechanics authority; normative rules remain in the numbered sections above.

### A.1 High-level game framing
*The Tower — Idle Tower Defense* combines persistent progression (labs, workshop, inventory/loadout systems) with run-time wave scaling pressure. In TowerSim v1, the practical question is not frame-perfect combat replay, but whether a fully specified build survives progressively stronger wave pressure long enough to reach higher waves.

### A.2 Why `MAX_WAVE` is the v1 objective
`MAX_WAVE` is a defensible deterministic objective because it can be derived from explicit stat inputs, deterministic mechanics, and authoritative tables without introducing sampling-based uncertainty. This keeps outcomes reproducible and auditable for the single-user workflow.

### A.3 How to read survivability outcomes
Survivability is interpreted through explicit envelopes and deterministic transforms, not hidden simulation. Where timing alignment uncertainty exists (for example, overlap-sensitive defensive effects), TowerSim treats uncertainty as bounded envelopes rather than stochastic trials.

### A.4 Guidance for Codex/ChatGPT implementations
When implementing or modifying behavior:
- treat this appendix as orientation only,
- source formulas/tables from authoritative hierarchy only,
- fail closed if required source data is missing,
- avoid inventing mechanics implied by narrative language.

