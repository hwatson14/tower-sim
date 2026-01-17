# Codex Operating Rules for TowerSim

These rules are binding for any agent or automated coding assistant working on this repo.

## Non‑negotiables
1. **Deterministic only**: no RNG, no sampling, no Monte Carlo.
2. **No invented mechanics**: implement mechanics only when backed by:
   - a pasted table / reference sheet provided by Harry, or
   - a cited Tower wiki page/section (link + brief excerpt/summary), or
   - an existing library table already in this repo with documented provenance.
3. **Fail‑closed**: if a required mechanic/table is missing or ambiguous, raise an explicit error and stop.
4. **One step per PR**: a PR should implement exactly one scoped increment.
5. **No silent changes**: every change must be explained in the PR description, including formulas and data sources.
6. **Tests required**: every new module must have unit tests. If a test depends on data snapshots, pin the snapshot.
7. **No drive‑by refactors**: do not reformat or rename unrelated code.

## Definition of done (per PR)
- Code compiles/imports.
- Unit tests pass.
- Any constants have a provenance note (sheet reference or wiki citation).
- Checklist updated (see ARCHITECTURE.md).

## Source of truth hierarchy
1. **Harry’s reference sheets** (authoritative).
2. Tower wiki (secondary; must be cited).
3. Existing repo libraries only if provenance is clear.

