# Optimisation Objectives
Version: phase4_v1
Layer: 4 — Optimisation Framework
Status: Refactored

## Purpose
Define the objective functions used to evaluate builds, loadouts, and stone allocation.

## Farming objective
Maximise blended:
- coins/hour
- cells/hour

Not equivalent to:
- raw DPS
- max wave
- generic survivability alone

### Operational implications
- kill timing matters
- kills inside bonus windows matter
- uncontrolled premature kills can reduce income
- survivability matters insofar as it increases productive wave density and bonus-window yield

## Tournament objective
Maximise:
- wave reached
- survival reliability

Secondary direct drivers:
- boss handling
- control reliability
- kill conversion

### Operational implications
- damage is useful only if it improves survival or boss throughput
- module choice must be evaluated against the survival envelope, not generic damage prestige

## Stone-allocation objective
Evaluate options against:
- immediate payoff
- survivability impact
- economy impact
- control of kill timing
- synergy with current shell
- lab burden
