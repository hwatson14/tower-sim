# Phase 3 Lab Tier-List KB Contract

## Purpose
Promote the workbook tier list into repo KB as **advisory metadata**, not as mechanical truth.

## Delivered artifacts
- `kb/labs/advisory/tables/lab-tier-list-v27_0_3.csv`
- `kb/labs/advisory/registry/lab-advisory-source-registry.csv`
- `out/lab_tier_list_advisory_v27_0_3.json`
- `out/lab_tier_list_advisory_summary.json`

## Semantics
This surface is:
- suitable for planners, optimisers, and advisors as a prior / heuristic / explanation aid
- unsuitable as authority for formulas, costs, durations, or runtime mechanics

## Required downstream behaviour
Consumers must:
1. join via `lab_canonical_id`
2. treat `ranking_primary` as the default prior
3. treat `ranking_conditional` as an optional scenario-dependent override
4. preserve notes for explanation
5. never let this surface override scenario-specific math when harder evidence exists

## Mapping policy
Primary mapping source:
- `kb/ledgers/sources/raw/repo-meta/registry/catalog.yaml`

Fallbacks:
- 4 explicit alias overrides for workbook names that differ from repo canonical naming:
  - Workshop Enhancements -> LAB_WORKSHOP_ENHANCEMENT
  - Enhancement Attack - Coin Discount -> LAB_ENHANCEMENT_ATTACK_COIN_DISCOUNT
  - Enhancement Defense - Coin Discount -> LAB_ENHANCEMENT_DEFENSE_COIN_DISCOUNT
  - Enhancement Utility - Coin Discount -> LAB_ENHANCEMENT_UTILITY_COIN_DISCOUNT
