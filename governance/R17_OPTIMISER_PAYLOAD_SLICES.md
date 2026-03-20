# R17 optimiser payload slices

This iteration adds domain-sliced optimiser payloads derived strictly from the whitelisted resolved rows in the R16 payload.

Slices emitted:

- survivability_inclusive
- damage
- economy

Design rules:

1. No new calculator canon or formulas were introduced.
2. Slices are projections of the existing whitelisted resolved payload only.
3. Survivability is broader than eHP and therefore includes boss-control support rows where relevant.
4. The full optimiser payload remains the master downstream contract; slices are convenience views.
