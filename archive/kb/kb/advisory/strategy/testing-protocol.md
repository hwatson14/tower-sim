# Optimisation Testing Protocol
Version: phase4_v1
Layer: 4 — Optimisation Framework
Status: Refactored

## Purpose
Define the experimental method for validating optimisation decisions.

## Farming A/B protocol
For each candidate preset, measure:
- coins/hour
- cells/hour
- run time
- wave reached
- observable kill timing inside BH / GT / DW bonus windows where possible
- death mode

## Tournament A/B protocol
For each candidate preset, measure:
- wave reached
- death mode
- boss survival pressure
- package dependency
- whether loss was wall collapse, chip overload, or boss throughput failure

## Stone-allocation test protocol
For each candidate spend option, score:
- immediate payoff
- survivability effect
- economy effect
- control of kill timing
- synergy with PC/BH shell
- lab burden

## Anti-hallucination protocol
1. Verify mechanics from the wiki or controlled reference artifacts.
2. Verify slot locks and assist unlocks.
3. Separate fact, inference, assumption, and account-specific observation.
4. Do not upgrade community heuristics into truth.
5. Prefer measured account results over prestige narratives.

## Recommended output format
- objective
- candidate options
- measured/known inputs
- reasoning
- recommendation
- uncertainty
- next test
