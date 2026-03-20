# Architecture Review and Optimisation Audit

## Scope of this audit
This audit reviews the docs pack as an architecture artifact and as a KB-aligned Tower design reference against the uploaded local package and chat decisions.

It is **not** a claim that every formula is already fully verified against the entire KB. It is an architecture and contract audit.

---

## Audit summary

### Overall verdict
The pack is now a **good build baseline**, but it is still strongest on architecture and weaker on formula-verification closure.

### Strengths
- top-level engine count is low and coherent
- ownership boundaries are much clearer than in the raw chat
- dynamic workshop progression is correctly treated as run state, not static baseline
- perk resolution is placed in the stat engine, which is cleaner for a fixed perk set
- scenario overlays are kept out of the stat engine
- temporary fallbacks are visible rather than hidden
- optimisation is correctly gated behind dependency clarity

### Main remaining weaknesses
- the effect-surface naming scheme is still a recommended pattern rather than a frozen repo contract
- boss heat-up is still a provisional implementation rule, not a closed verification item
- orb and electron cadence remain explicit gaps
- the workshop dependency ledger is first-pass architecture, not a closed verified lineage map
- some docs still talk at the family level rather than track-ID level

---

## Detailed review findings

### 1. Top-level architecture
**Assessment:** Strong

The three-engine split is now cleaner than the earlier multi-engine variants because it aligns to state-change class:
- fixed contributor resolution
- scenario overlay and invariant derived effects
- dynamic progression state

This is the biggest structural improvement.

### 2. Stat engine boundary
**Assessment:** Strong, with one caveat

Putting fixed perk resolution into the stat engine is the correct simplification for a fixed perk set.

The caveat is that the stat engine must not absorb mode/BC/heat. The docs now consistently keep those outside, which is good.

### 3. Scenario-invariant engine boundary
**Assessment:** Good

This layer now has a clear reason to exist:
- it centralises reusable fixed-for-run cadence, uptime, interval, resistance, and overlap surfaces
- it avoids duplicating scenario overlays across boss and future econ work

The biggest unresolved point is final naming/contract freeze for emitted effect surfaces.

### 4. Progression engine boundary
**Assessment:** Strong

The docs now correctly treat workshop transitions, wave state, and combat state as owned by progression.

The insistence on tracking all workshop levels even if only a subset is consumed in boss-v1 is correct and future-safe.

### 5. KB alignment discipline
**Assessment:** Mixed but honest

The pack does a good job of marking open items instead of pretending closure.
That is the right fail-closed behaviour.

However, the pack is still not a formula-verified handover. It is a governed architecture handover.
That distinction should remain explicit.

### 6. Optimisation readiness
**Assessment:** Not ready for aggressive optimisation yet

The correct optimisation posture is already stated:
- use full safe recompute in v1
- optimise later only after dependency and formula ledgers are explicit and tested

This is correct. Any earlier optimisation would likely create silent drift.

---

## Recommended optimisations applied in this v2 doc pack

### Optimisation 1: reduced top-level engine count
Old conversational direction briefly risked too many top-level engines. This pack now keeps three only.

### Optimisation 2: perk simplification
A separate top-level perk effects engine was removed in favour of a stat-engine submodule.

### Optimisation 3: explicit effect-surface contract
The pack now has a dedicated surface contract so helper values do not leak into code under vague names.

### Optimisation 4: explicit dependency ledger
The workshop dependency ledger now makes later recompute optimisation discussable without coding blind.

### Optimisation 5: stronger status language
The pack more clearly distinguishes:
- locked architecture
- temporary fallback
- provisional implementation rule
- open verification task

---

## Risk ledger

| Risk | Severity | Status | Note |
|---|---:|---|---|
| Boss heat-up formula not fully closed | High | Open | Provisional implementation rule only |
| Plasma Cannon resolved surface missing | High | Open | Temporary fallback in place |
| Orb cadence surface missing | Medium | Open | Needs governed surface or explicit scenario override |
| Electron cadence surface missing | Medium | Open | Needs governed surface or explicit scenario override |
| Workshop dependency ledger not fully KB-verified | High | Open | Full safe recompute still required |
| Effect-surface naming not finally frozen | Medium | Open | Pattern exists, final contract still needed |

---

## What should change next

### Highest-value next artifacts
1. `12_formula_verification_ledger.md`
2. `13_module_file_design.md`
3. `14_boss_wave_test_plan.md`

### Why
Because the architecture is now sufficiently coherent that the main remaining risk is silent formula drift, not top-level structure drift.

---

## Final audit conclusion
As an architecture pack, this v2 is materially stronger than v1 and is suitable as the new iteration baseline.

As a fully verified KB formula pack, it is not closed yet.
That is acceptable, provided future work does not blur that distinction.


## v100 integration pass
This review was updated after ingesting the completed v100 calculator package.

### Improvements from v100
- Plasma Cannon emitted runtime surface now exists
- perk resolution is confirmed inside the calculator/compiler path
- several boss-engine-critical surfaces are confirmed publishable outputs

### Open items that remain
- boss heat-up formula closure
- governed orb/electron cadence surfaces
- workshop dependency proof closure for all progression-relevant tracks
