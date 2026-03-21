# Economy tables

Active tables:
- `currency-summary.csv`
- `economy-resource-flows.csv`
- `resource-entity-registry.csv`
- `vault-overview.csv`
- `vault-tree-registry.csv`
- `vault-tier-rules.csv`
- `vault-power-single-level-nodes.csv`
- `vault-contributor-routing.csv`
- `vault-node-effect-registry.csv`
- `vault-externalized-simulator-inputs.csv`
- `vault-simulator-boundary-registry.csv`

Notes:
- Vault structure, tree rules, node routing, and single-level exceptions are normalized for simulator-facing use.
- Vault numeric node bonuses that do not have bundled ladders are handled through an explicit externalized-input boundary rather than silent inference.
- These vault boundaries are accepted package policy, not open simulator blockers.
