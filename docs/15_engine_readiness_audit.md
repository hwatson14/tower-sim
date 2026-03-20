# Engine Readiness Audit

## Question
Are the scenario and progression engines fully defined and accurate now?

## Verdict
### Scenario-invariant engine
**Mostly yes at the architecture/contract level, not fully at the emitted-surface closure level.**

What is defined well enough now:
- ownership of `mode_id`, BC, and heat
- ownership of accepted model constants and fixed-for-run overlays
- consumption of stat-engine emitted runtime/mechanic surfaces

What is still not fully closed:
- governed orb boss cadence surface
- governed electron cadence surface
- final choice of whether some scenario outputs should be published under existing namespaces or remain internal

### Progression engine
**Defined well enough to start implementation scaffolding, but not fully formula-closed for a production-accurate boss engine.**

What is defined well enough now:
- mutable workshop run-state ownership
- attack-wave vs health-wave separation
- stat-engine full recompute requirement
- boss TTK-before-intake causality
- wall survival as primary v1 death condition
- perk timeline consumption rule: progression reads the generated timeline, but does not own PWR timing logic

What still needs closure or explicit override policy:
- orb boss cadence
- electron cadence
- exact runtime event ordering details beyond already-closed mechanics
- full track-level dependency proof if you want optimized recompute later

## Recommended implementation posture
- **Yes**: start implementation of scaffolding and controlled v1 engine logic now
- **No**: do not pretend the progression engine is fully closed for final-accuracy boss simulation yet

## Build rule
Implement with:
1. full safe recompute
2. explicit scenario overrides for blocked cadence items
3. no stale fallbacks for already-emitted surfaces
4. provenance tags preserved in docs/comments
