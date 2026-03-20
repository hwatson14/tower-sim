# Enemy Scaling Curves

Status: quantitative surface present.

## What is actually present
The KB now contains raw enemy HP and damage anchor tables internalized into this package plus long-form expansions by wave and surface.

## Recommended use
1. Read exact values at anchor waves from the raw tables.
2. Use the bundled interpolation rule between anchors.
3. Treat older conceptual exponential descriptions as approximate summaries, not canonical numeric truth.

## Remaining caution
Enemy-type-specific modifiers, fleets, bosses, heat, and battle conditions still belong in separate mechanic layers and should not be baked into the base HP/damage tables.
