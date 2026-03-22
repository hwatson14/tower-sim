# Lab tier-list advisory note

This surface is intentionally stored under `kb/labs/advisory/` to keep it separate from mechanical lab tables.

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
