# Lab System

## Core structure
Labs are persistent research upgrades that primarily extend scaling, modify caps, or unlock additional systems. Most labs are milestone-gated before they become researchable.

## Canonical surfaces
- `kb/labs/tables/lab-values.csv`
- `kb/labs/tables/lab-track-summary.csv`
- `kb/labs/tables/lab-application-registry.csv`
- `kb/labs/tables/lab-source-registry.csv`
- `kb/labs/tables/wiki-game-speed-lab.csv`
- `kb/labs/tables/module-drop-labs.csv`
- `kb/labs/tables/lab-simulator-boundary-registry.csv`
- `kb/labs/contracts/lab-runtime-application-contract.md`

## Interpretation rules
- Generic lab ladders and specialized lab families should not be flattened into a single progression concept.
- Battle-condition reduction labs belong semantically to tournaments even though they are researched in labs.
- Wall labs and module labs are subfamilies with their own unlock and effect semantics.
- Exact level lookups must come from `lab-values.csv`; summary tables exist only to support routing and audit.
- If a simulator-relevant lab appears in `lab-simulator-boundary-registry.csv`, treat that file as a scope/boundary registry rather than permission to invent a curve.
