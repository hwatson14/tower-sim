# Decision Summary

## Locked decisions from this chat

### 1. Scope rail
The build must stay on the wave engine scope and avoid turning into a generic full combat simulator.

### 2. KB-aligned rule
All formulas and emitted surfaces must be KB aligned and verified. Unsupported assumptions must be flagged, not smuggled in.

### 3. Canonical dependency
The wave engine must use canonical composite stats as calculated by the stat engine. It must not independently recreate permanent account stat logic.

### 4. V1 focus
V1 is a **boss-wave-focused** progression engine, not a full wave replay engine.

### 5. Separate attack and health wave
The engine must track both:
- `attack_wave`
- `health_wave`

Reason:
- boss outgoing damage depends on attack wave
- boss HP depends on health wave
- this separation is required for future v2 damage-model expansion even though v1 damage sources are percent-based

### 6. V1 boss TTK first
The engine must first compute **time to kill the boss**, then compute boss outgoing damage over that TTK window.

### 7. V1 allowed boss damage sources
For v1 boss TTK, only these kill sources are in scope:
- Plasma Cannon
- Thorns
- Orbs
- Electrons

### 8. V1 damage-source character
All v1 damage sources are percent-based.

### 9. Battle conditions matter
Battle conditions must be applied to v1 boss kill and intake logic where relevant.

### 10. Boss heat-up matters
The engine must include boss damage heat-up in intake modeling.

### 11. Wall is the practical survival surface
For v1, wall survival is the operative death condition. Tower HP does not need to be carried as a primary survival state.

### 12. BH and CF matter via mitigation
Black Hole and Chrono Field matter because they contribute to the effective damage reduction / mitigation envelope.

### 13. Workshop state is dynamic and must be tracked
Because workshop can be respec'd and not all tracks are maxed before a run, the progression engine must track **all current workshop levels** as run state.

### 14. Stat recalculation is required
Since in-run workshop changes alter derived stats, the progression engine must call a KB-aligned stat recalculation path.

### 15. Correct baseline stage
The engine should start from a `start_of_run` baseline, not `max_progression`.

### 16. Modes
The architecture should support these three mode IDs:
- `farming`
- `tournament`
- `milestone`

### 17. Perk set rule
The perk set is fixed for the entire run.

### 18. Perk placement
Perk effect resolution should be folded into the stat engine, not kept as a separate top-level engine.

### 19. Scenario overlays
Mode, battle conditions, and heat/environment overlays should not be owned by the stat engine. They belong in the scenario-invariant derived effects engine.

### 20. Legacy perk engine reuse
The uploaded legacy perk package is partially reusable:
- good seed for perk selection/timeline concepts
- not safe to adopt as-is
- naming and old-repo assumptions require migration

### 21. Engine count
Current preferred top-level architecture is exactly three engines:
- stat engine
- scenario-invariant derived effects engine
- progression engine

### 22. Verification rule
Optimisation is allowed only after the dependency and formula surfaces are explicit enough to audit.
