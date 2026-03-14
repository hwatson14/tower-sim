# Runtime Ordering Evidence

## Public-source verified
- Defense Percent is applied before Defense Absolute.
- Separate damage reduction sources including Chrono Field Damage Reduction, Primordial Collapse, and Flame Bot apply after Defense Absolute.
- Chrono Field Damage Reduction specifically is taken on enemy damage after Defense Absolute is calculated.

## User-observed evidence
- Wall takes contact first while alive; tower HP is only hit once wall is down.
- Thorns damage occurs after wall or tower HP loss.
- The same contact can both damage wall/tower and kill the enemy with thorns.
- Saboteur is blocked by wall.
- Wall rebuild pushes enemies outside wall range.
- Practical permanent uptime behavior is gapless when cooldown equals duration exactly.
- Attack Speed behaves continuously in play.
- Game speed changes affect the whole game, but displayed numbers are not always exact.

## Effective Paths evidence class
- Effective Paths contains modeling and approximation notes and should not be used as sole authority for same-tick precedence.
- Home Page!O26 warns that several things are hard to compute, including AOEs and attack speed.
- Home Page!P28 states Attack Speed uses a custom imprecise formula and does not reflect the actual in-game value.

## Remaining unresolved / low-materiality
- Boss-specific Orb Boss Hit same-moment precedence versus other damage is not resolved and is currently treated as low-materiality and open.
