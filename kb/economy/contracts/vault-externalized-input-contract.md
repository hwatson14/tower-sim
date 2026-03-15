# Vault externalized input contract

## Purpose
This contract defines how simulator consumers must handle vault-linked numeric bonuses that are accepted as explicit account-resolved inputs because the package does not bundle an authoritative per-level ladder for every vault stat node.

## Active externalized vault inputs
See `kb/economy/tables/vault-externalized-simulator-inputs.csv`.

## Rule
When a vault node is listed in `vault-externalized-simulator-inputs.csv`, the simulator may treat the resolved account-instance bonus for that exact mapped destination as an explicit input surface.

## Required behavior
1. Accept the resolved value only when the vault node is explicitly listed as externalized.
2. Apply the value only to the mapped destination field in `vault-node-effect-registry.csv`.
3. Preserve provenance that the value was externally supplied rather than derived from bundled vault ladders.
4. Fail closed when a simulation requires a listed vault input and no explicit value is supplied.

## Prohibited behavior
- Do not invent, interpolate, or reverse-engineer vault ladders from tree tier counts.
- Do not infer numeric node values from advisory notes or summary pages.
- Do not promote an externalized account input into fake global canon.

## Closure note
Vault is considered closed for simulator use when structural tables, single-level nodes, and this explicit externalized-input boundary are all respected together.
