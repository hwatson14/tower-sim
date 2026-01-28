# Battle Conditions + Heat: Evidence & Gaps (Wiki-derived)

This repo is fail-closed. We only treat numeric tables as "known" if sourced from Effective Paths or explicit wiki tables.

## Confirmed (wiki)
- Heat exists in tournaments and ramps to a maximum at wave 1000 (shape not specified in the wiki sources located so far).
- "More Bosses" in tournaments is a special case that does NOT heat up over waves; it is static per league.
  - Bronze: boss every 10 waves
  - Silver: boss every 9 waves
  - Gold: boss every 8 waves
  - Platinum: boss every 7 waves
  - Champion: boss every 6 waves
  - Legends: boss every 5 waves

## Critical semantic note
Tournament runs do **not** apply every battle condition at once. A league defines
"More Bosses" plus a small number of additional BCs (random pool), and
Platinum+ also includes either "Death Defy Down" or "Energy Shields Down".

See: `adapter/tournament_bc_selection.py` for the fail-closed enumerator.

## Still missing (must be populated from authority sources)
- Full heat curve per league (wave 1..1000 -> heat scalar).
- Base magnitudes for each BC at a given BC 'level' (e.g., Orb Resistance Lvl 50 -> x%).
- How 'heat scalar' maps to magnitude (linear? piecewise? none specified in wiki sources found).

## Protocol
1) Populate heat curves from Effective Paths or a wiki table that explicitly lists per-wave values (or an explicit formula).
2) Populate BC base magnitude from Effective Paths or explicit level->effect wiki tables.
3) Then apply BC lab reductions (wiki tables for BC reduction labs exist).
