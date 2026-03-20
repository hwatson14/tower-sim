# Wiki labs baselines

## Verified structural facts
- Laboratory is a distinct progression surface for upgrades different from Workshop.
- Lab upgrades generally help with scaling, caps, unlocks, or modifiers.
- Most labs are milestone-gated before they become researched.
- Labs Speed reduces research time but does not retroactively reduce the time of subsequent Labs Speed levels themselves.

## Quantitative source choice
`kb/labs/tables/lab-values.csv` is the active bundled ladder surface for the 11 promoted lab families.
The paired raw sources are recorded in `kb/labs/tables/lab-source-registry.csv`.

## Explicit simulator boundary or package choice
The active bundled package does not yet contain a source-backed ladder for Wall Fortification.
Models must fail closed on that surface rather than inventing a curve.
