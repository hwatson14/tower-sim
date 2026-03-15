# Lab closure status

## What is now closed
The active package now contains:

- a bundled active long-form ladder surface for simulator-relevant lab families
- a per-lab application registry defining destination entity and stat semantics
- a source registry showing the bundled raw source for each active ladder family
- an explicit scope/boundary registry for simulator-relevant lab decisions

## What changed versus earlier package state
Earlier package ledgers treated lab closure as blocked by both Defense % and Wall Fortification.
The bundled package already contains a source-backed Defense % ladder and it is now explicitly routed as active canon.

## Current package choice
- `LAB_WALL_FORTIFICATION` is no longer treated as an open simulator gap.
- Wall Fortification unlock is resolved in-package as **Tier 14 / Wave 60**.
- Any remaining exact-runtime timing edge around wall interactions is governed by the global simulator-scope boundary policy rather than lab-specific boundary status.
