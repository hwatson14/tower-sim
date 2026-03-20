# Core System Interactions

This file was introduced in KB v8 to store reasoning context, not just raw tables.

## Heat mechanic
Recorded model:
enemy_damage = base_damage × (1.04 ^ hits_taken)

Interpretation:
- High attack-speed control loops can unintentionally amplify enemy damage.

## Coin decay
Recorded rule:
- Enemy coin value becomes 50 percent of base after 3 waves alive.

Implication:
- Farming depends on kill timing and cleanup, not just survival.

## Protector interaction
Recorded behavior:
- Enemies inside Protector shielding cannot be orb-killed.

Implication:
- Protector presence breaks simple orb-funnel assumptions.

## Fleet interaction summary
- Fleet enemies ignore large parts of the standard control toolkit.
- Treat fleet waves as anti-control pressure events.
