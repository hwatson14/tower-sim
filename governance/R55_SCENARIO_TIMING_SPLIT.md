# R55 Scenario + Timing Engine Split

## Decision
The former mixed scenario/timing owner has been removed.

## Final ownership
- `engine/scenario_engine.py` owns scenario/world assumptions only.
- `engine/timing_engine.py` owns cooldown, duration, uptime, phase, overlap, and shared-cycle timing logic.
- Progression, optimiser, and analysis consumers must call those real owners directly.

## Why
The prior mixed engine blurred scenario state with temporal mechanic interaction. That would have caused repeated leakage of uptime and overlap logic into econ, DR, and progression consumers.

## Scope completed here
- deleted `engine/scenario_invariant_engine.py`
- created `engine/scenario_engine.py`
- created `engine/timing_engine.py`
- rewired active tests to the split engines
- rewired optimiser timed econ overlap to call `timing_engine`

## Remaining downstream migration
- progression engine should consume timing surfaces directly when runtime active-state windows matter
- additional DR overlap consumers should move to timing engine over time
