# State semantics

This document records the canonical state semantics for IDS-facing canonical flows.

## Preset naming

Canonical preset names are:
- Tourney
- Farming
- Milestone
- Preset 4
- Preset 5

Raw aliases are normalized only at ingestion boundaries:
- `Preset 3` -> `Milestone`
- `Testing` -> `Milestone`
- `Placeholder 4th preset` -> `Preset 4`
- `Placeholder 5th preset` -> `Preset 5`

After ingestion, non-canonical preset names are invalid.
Canonical artifacts, tests, fixtures, and runtime inputs must use canonical names only.

## Value semantics

- **missing** = absent required preset, lane, or field. Missing is invalid in canonical flows and must fail closed.
- **empty** = explicitly present but empty. Empty is valid and explicit.
- **zero** = valid numeric zero. Zero is distinct from missing and empty.
- **invalid** = unrecognized name, shape, or value. Invalid must fail closed.
- **synthetic** = transient non-canonical runtime or compare state. Synthetic state must be explicitly typed/quarantined and must never be serialized as canonical preset state.
- transient/non-canonical perk preset namespaces must be explicitly tagged as transient before canonical compilation is allowed to accept them.

## Fallback policy

Canonical flows must not fail open.
The following are forbidden as silent fallback behavior in canonical flows:
- default preset substitution for invalid inputs
- fallback to `Farming`
- fallback to empty list
- fallback to zero

## Current encoding boundary

These semantics are encoded at the current preset-binding boundaries by:
- loading canonical preset and alias truth from `registry/preset_contract.yaml`
- restricting alias normalization to ingestion helpers
- rejecting invalid preset names in canonical runtime/loadout inputs
- rejecting invalid/non-canonical perk preset names unless the config explicitly declares a transient preset namespace class
- preserving explicit empty preset containers as valid values instead of rebinding them
