# Domain Completeness Audit

This audit is the active package-level answer to the question: **what parts of the Tower KB are closed, partial, or still unsurfaced?**

## Scope of this audit
This is a package audit, not a claim that the real game is fully solved.
It classifies the **bundled KB surfaces** only.

## Main conclusion
The KB is strong on:
- workshop and enhancements
- enemies and tournament battle conditions
- combat runtime contracts for material ordering
- modules and major ultimate-weapon ladders
- naming, alias, and contributor-routing governance

The KB is still weaker on:
- broad normalized economy surfaces
- dedicated relic value surfaces
- dedicated player-stuff surfaces
- dedicated theme/song and unlock surfaces
- evenness of named per-UW and per-bot structured tables
- a few formula-family gaps still flagged by the bundled Effective Paths mechanics-library audit

## Read these tables first
1. `tables/domain-completeness-ledger.csv`
2. `tables/subsystem-completeness-ledger.csv`
3. `tables/source-family-surface-audit.csv`
4. `tables/formula-coverage-ledger.csv`
5. `tables/effective-paths-formula-registry.csv`

## Interpretation rule
- `closed` or `closed_for_active_use` means the package has a clear active canonical surface for that area.
- `mostly_closed` means the package is strong but still has a narrow, explicit remainder.
- `partial_structured` means some useful canon exists, but the area is not yet fully normalized or evenly surfaced.
- `sourced_but_unsurfaced` means supporting evidence or routing exists, but the KB does not yet expose a dedicated active value surface.
- `explicit_unknown_to_community` remains an intentional boundary, not a hidden defect.

## Why this audit exists
Without a package-wide completeness ledger, a KB can look polished while still hiding thin spots. That is clown makeup on a goblin. This audit is meant to prevent that.
