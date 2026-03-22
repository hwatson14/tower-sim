# Lab tier-list advisory note

This surface is intentionally stored under `kb/labs/advisory/` to keep it separate from mechanical lab tables.

## Archive provenance
This table is the advisory-only portion of the R93 archive import.

Archived workbook rows are preserved with:
- canonical `lab_canonical_id` joins
- workbook row numbers
- source workbook, sheet, and version strings
- primary and conditional ranking fields
- original note text

Canonical ID mapping follows the repo catalog with only four explicit manual alias overrides:
- Workshop Enhancements -> `LAB_WORKSHOP_ENHANCEMENT`
- Enhancement Attack - Coin Discount -> `LAB_ENHANCEMENT_ATTACK_COIN_DISCOUNT`
- Enhancement Defense - Coin Discount -> `LAB_ENHANCEMENT_DEFENSE_COIN_DISCOUNT`
- Enhancement Utility - Coin Discount -> `LAB_ENHANCEMENT_UTILITY_COIN_DISCOUNT`

## Why
The workbook tier list is a judgement surface:
- it contains rankings such as `S+`, `A`, `QOL`, `F`
- it includes conditional ranks and human notes
- it reflects strategy guidance, not game formulas

## What should survive refactor
Even if file locations change, preserve:
- one row per workbook lab
- canonical lab ID mapping
- primary rank
- conditional rank
- note text
- provenance and advisory status

## What should not happen
Do not:
- merge this into `kb/labs/tables/lab-values.csv`
- present it as mechanic truth
- use it as sole ranking authority once scenario- and account-aware optimisers exist
- wire the archive ranking fields into runtime formulas or optimizer scoring
- land thorns or enemy-level-skip battle-condition runtime query surfaces from this archive tranche
