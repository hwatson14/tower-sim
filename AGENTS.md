> **Role:** Normative agent operating rules for TowerSim.

# Codex Operating Rules for TowerSim

If any instruction conflicts with repository docs, [`CONTRACT.md`](./CONTRACT.md) is authoritative.

## 1) Core non-negotiables
1. **Deterministic only, except perk-order artifacts**: no RNG, no sampling, no Monte Carlo.
2. **No invented mechanics**: implement mechanics only with authoritative provenance.
3. **Fail-closed**: if a required mechanic/table/input is missing or ambiguous, raise explicit errors and stop.
4. **No silent changes**: behavior/data-source changes must be explained in PR notes.
5. **Minimal files / no doc sprawl**: prefer editing existing files and deleting/merging redundant docs.
6. **No drive-by refactors**: do not rename/reformat unrelated code.

## 2) Source and mechanics rules
- Source hierarchy: Harry sheets > cited wiki > existing repo tables with provenance.
- All mechanics/formulas must route through `mechanics/manifest.yaml`.
- Do not bypass manifest-driven mechanics loading at runtime.
- Do not create new mechanics packs/files unless explicitly requested.

## 3) Scope discipline
- Implement only what was requested.
- For doc-only tasks: change docs and minimum enforcement needed for green checks.
- Do not change runtime behavior unless explicitly in-scope.

## 4) File-creation policy
Before creating any new file:
- Search for an existing file that can be updated.
- Prefer updating canonical docs over adding parallel docs.
- If unavoidable, justify in PR body why edit-only was insufficient.

## 5) Required PR content (agent checklist)
Include in every PR message:
- concise summary of changes,
- provenance notes for mechanics/constants/data decisions,
- commands run locally with outcomes,
- explicit statement of scope boundaries,
- known gaps or follow-up items.

## 6) Testing and validation expectations
- Run relevant checks for touched areas (at minimum, structure checks for doc/governance changes).
- Report command output honestly; do not claim green checks without execution.
- If environment limitations block checks, state limitation explicitly.

## 7) Preferred operating behavior for this repo
- Be explicit, deterministic, and conservative.
- Choose simpler implementation over generalized abstraction.
- Keep documentation detailed but concentrated into the minimal authoritative file set.
