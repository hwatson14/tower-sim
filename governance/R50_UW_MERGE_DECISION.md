# R50 UW Merge Decision

Merged admissible UW-specific slices from r49 integration into the current baseline.

Accepted:
- IDS current-value preservation for UW tracks
- fraction-to-pct normalization for relevant UW IDS fields
- Chrono Field duration on canonical mechanic_param path
- mechanic_param routing for existing state-queryable UW canonicals
- KB registry additions for remaining wiki-confirmed UW gap rows
- lab unlock-base contributor splits for Smart Missiles Explosion, Missile Barrage, and Poison Swamp Stun
- unified mechanic_param::uw.* stat-engine composition path for stateful UW canonicals

Rejected:
- all coin-surface regressions from intake
- any remapping of economy.coin_multiplier back onto legacy coin_kill surfaces

Deferred:
- chrono_jump canonical rename review remains open; current intake name preserved pending explicit downstream rename sweep
