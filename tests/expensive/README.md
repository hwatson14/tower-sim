# tests/expensive/

This directory contains tests that are too slow or resource-intensive for the default live gate.

Tests here are NOT included in `pytest tests/live`. Run them explicitly with `pytest tests/expensive`.

## Current contents

Intentionally minimal at this tranche. Long-running regression suites (e.g. full perk-scaling
matrix, boss-wave numeric regression, full scenario-timing split) are candidates for migration
here in future tranches.
