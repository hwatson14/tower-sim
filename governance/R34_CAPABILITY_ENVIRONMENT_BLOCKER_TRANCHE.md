# R34 Capability and Environment Blocker Tranche

Closed in this tranche:
- Extra Black Hole -> capability.uw.black_hole.extra_black_hole
- Black Hole Disable Ranged Enemies -> capability.uw.black_hole.disable_ranged
- Chain Lightning Shock -> capability.uw.chain_lightning.shock
- Swamp Stun -> capability.uw.poison_swamp.stun
- Missiles Explosion -> capability.uw.smart_missiles.explosion
- Battle Condition Reduction -> environment_param::bc.reduction.generic_pct

Implementation notes:
- Added lab application registry rows for boolean unlock labs and generic BC reduction.
- Added compiler support for lab application rows with operation_type=enable to publish bool contributors.
- Added lab summary/value rows for one-level capability labs and imported BC reduction ladder from bundled tournaments table.
- Did not force scalar follow-on labs such as Swamp Stun Chance/Time or Missile Radius in this tranche.
