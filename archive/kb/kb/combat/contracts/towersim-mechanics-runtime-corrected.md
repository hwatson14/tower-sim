# TowerSim Runtime Mechanics Reference
Status: evidence-tiered runtime reference
Layer: 2 — Runtime Mechanics

## Purpose
This document defines runtime behavior after static stats already exist.

It governs:
- contact mechanics
- orb-family mechanics
- enemy-class interactions
- wall runtime behavior
- ultimate weapon runtime channels
- card runtime behavior
- battle-condition runtime effects
- module unique runtime behavior

It does not govern:
- contributor rows
- canonical contributor naming
- scaling tables
- optimisation logic

## Evidence tiers
- public_source: verified from public wiki/source surfaces
- user_observed: observed in play and retained explicitly as non-public evidence
- boundary: left out of scope or explicitly bounded rather than invented

## Rule schema
Each runtime rule should be represented with:
- mechanic_id
- rule_confidence
- token_confidence
- token_status
- rule
- engine_interpretation

## Runtime domains

### 1. Damage resolution
Closed ordering in this layer now includes:
1. Defense Percent occurs before Defense Absolute. [public_source]
2. Separate DR sources including Chrono Field Damage Reduction, Primordial Collapse, and Flame Bot apply after Defense Absolute. [public_source]
3. Chrono Field damage reduction specifically applies after Defense Absolute. [public_source]

The full end-to-end same-tick precedence model is intentionally out of KB scope unless a future task explicitly requires frame-exact simulation semantics.

### 2. Sustain systems
- recovery packages are a runtime sustain subsystem with a maximum recovery concept
- ally package behavior is distinct from ordinary package behavior and can exceed the maximum recovery limit

### 3. Contact mechanics
- wall takes contact first while alive; tower HP is only hit once wall is down [user_observed]
- thorns damage occurs after wall or tower HP loss [user_observed]
- the same contact can both damage wall/tower and kill the enemy with thorns [user_observed]
- Saboteur is blocked by wall [user_observed]
- wall rebuild pushes enemies outside wall range [user_observed]

### 4. Orb systems
- base orbs and extra orbs are separate runtime families
- boss/elite/fleet interactions must be handled through exception matrices
- boss orb hit is a special exception case, not generic orb kill

### 5. Enemy-class interactions
Enemy classes should be normalized through a matrix, not prose:
- normal
- boss
- elite
- fleet

### 6. Wall runtime behavior
- wall blocks until depleted [user_observed/public_behavior]
- wall regen depends on tower regen relationship
- fortification allows above-base wall HP state
- wall rebuild pushes enemies outside wall range [user_observed]

### 7. Ultimate weapon runtime channels
Runtime channels should be separated by effect, for example:
- Black Hole: pull, damage, coin_bonus
- Death Wave: effect_tag, health_bonus, coin_bonus, armor_stripping
- Poison Swamp: entry stun and other runtime channels
- Chrono Field: speed and damage-reduction effects
- Spotlight: non-percent and non-wave-stat damage multiplier channel

### 7A. Timing and continuity
- exact cooldown equal to exact duration produces gapless uptime in practice [user_observed]
- Attack Speed behaves continuously in play [user_observed]
- game speed affects the whole game; displayed numbers are not always exact [user_observed]
- Effective Paths approximation notes must not be promoted into same-tick precedence canon

### 8. Battle Conditions
Battle Conditions are runtime effect modifiers and belong in Layer 2 behavior plus Layer 3 quantitative values.
Only behavioral truth is hardened here. Exact numeric magnitudes remain Layer 3 work.

### 9. Module unique runtime behavior
Module uniques should be normalized by:
- trigger
- target
- effect_type
- behavior
- exclusions_or_exceptions

Only a reduced high-signal subset is retained here. Broader module-catalog work remains pending exact verification.

## Current hardening posture
This file is the narrative contract only.
All operational runtime behavior should be implemented from the structured CSV/YAML artifacts that sit beside it.
