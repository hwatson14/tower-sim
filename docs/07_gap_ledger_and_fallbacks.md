# Gap Ledger and Fallbacks

## Rule set
- Every temporary fallback must be explicit.
- Every temporary fallback must have an exit condition.
- No temporary fallback should masquerade as final canonical truth.

---

## Gap A: Plasma Cannon effect surface
### Status
A clean emitted Plasma Cannon boss-damage effect surface is not yet available from the current stat-engine outputs.

### Temporary handling
Use a temporary fallback adapter based on selected card state/level.

### Required tag
`TEMPORARY_FALLBACK__remove_when_stat_engine_emits_plasma_cannon_effect_surface`

### Exit condition
Remove the fallback once the calc emits the governed resolved PC effect surface.

---

## Gap B: Orb boss-hit cadence
### Status
Not yet locked as a governed emitted surface.

### Temporary handling
Use a scenario override or provisional scenario-invariant runtime parameter.

### Exit condition
Promote to a verified scenario-invariant emitted surface if needed.

---

## Gap C: Electron boss-hit cadence
### Status
Electron count exists, but cadence/contact frequency is not yet locked as a governed emitted surface.

### Temporary handling
Use a scenario override or provisional scenario-invariant runtime parameter.

### Exit condition
Promote to a verified scenario-invariant emitted surface if needed.

---

## Gap D: Exact boss heat-up wording/model
### Status
A working model was discussed, but full KB verification is still required.

### Temporary handling
Use the documented linear +4% per completed prior hit model as the v1 working rule.

### Exit condition
Replace only if stronger KB evidence contradicts it.

---

## Gap E: Full workshop dependency ledger
### Status
Partially closed in v2. A first-pass ledger now exists, but KB verification of every workshop track and downstream surface link is still required.

### Temporary handling
Use full safe recomputation rather than dependency-pruned recompute.

### Exit condition
Dependency-aware optimization can only happen after the dependency ledger is verified and regression-tested.
