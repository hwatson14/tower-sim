# R10 Helper Output Plane Policy

## Decision

Helper formulas should remain in the calculator system and should eventually be emitted once the helper plane is implemented.

They should **not** be forced into the main canonical stat plane.

## Output planes

1. `canonical`
   - core broadly useful tower/account surfaces
2. `runtime_mechanic`
   - mechanic parameters, cooldowns, durations, counts, toggles
3. `helper_optimizer`
   - derived helper formulas, strategy-support formulas, optimizer-facing aggregates

## Current recommendation

- retain all helper formulas in KB/governance immediately
- mark them explicitly as helper formulas
- plan eventual emission through `helper_optimizer`
- do not require one-to-one canonical stat promotion first

## First emitted helper row candidates

These are the clearest near-term helper/optimizer rows because the calculator already has destination support but does not currently emit them:

- `uw.black_hole.coin_bonus_multiplier`
- `uw.death_wave.coin_bonus_multiplier`
- `uw.spotlight.coin_bonus_multiplier`

## Manual closures accepted this iteration

- `EPD_SPB` is treated as a helper for Standard Perk Bonus application
- `EPD_SHOCKWAVE_DAMAGE` is treated as a helper derived from ACP plus shockwave cadence/size inputs

## Candidate inventory

- total helper-plane candidates tracked: 32
- near-term emit candidates: 3
- later complex-mechanics/helper-plane candidates: 29

## Guardrails

- helper formulas may be emitted even when not first-class canonical stats
- helper formulas must be visually and contractually distinguished from canonical outputs
- optimizer may consume both canonical and helper outputs, but must know the plane for each row
- helper emission should not be used to imply complete runtime-mechanics coverage
