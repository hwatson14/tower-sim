# Survivability and Wave Death Model

## Goal
Estimate why a run dies and what subsystem must improve to extend it.

## Core failure inequality
incoming_effective_dps > sustain_capacity

Where sustain_capacity includes:
- health buffer
- wall buffer
- regen
- lifesteal
- mitigation layers
- control preventing contact

## Distinct death modes
### Boss death
Boss survives burst chain and reaches the tower with enough health to outpace sustain.

### Fleet death
Combined burst from simultaneous enemies exceeds regen and wall buffer.

### Protector stall death
Protectors keep enemies alive long enough for density and contact pressure to snowball.

### Control collapse
Enemy speed, attack speed, or BC pressure reduces the time available to kill before contact.

## Wave-death prediction method
1. Identify death mode.
2. Identify limiting layer: buffer, mitigation, control, or kill conversion.
3. Compare upgrade candidates by which layer they improve.
4. Prefer the smallest upgrade that moves the limiting inequality back below threshold.
