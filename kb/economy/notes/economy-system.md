# Economy system

Scope:
- currencies and broad resource flows
- Vault tree structure and routing
- simulator boundary for vault-linked numeric bonuses

Key active surfaces:
- `kb/economy/tables/currency-summary.csv`
- `kb/economy/tables/economy-resource-flows.csv`
- `kb/economy/tables/resource-entity-registry.csv`
- `kb/economy/tables/vault-overview.csv`
- `kb/economy/tables/vault-tree-registry.csv`
- `kb/economy/tables/vault-tier-rules.csv`
- `kb/economy/tables/vault-power-single-level-nodes.csv`
- `kb/economy/tables/vault-contributor-routing.csv`
- `kb/economy/tables/vault-node-effect-registry.csv`
- `kb/economy/tables/vault-externalized-simulator-inputs.csv`

Interpretation:
Economy now includes normalized resource and vault-tree registries, routing, tier rules, single-level exceptions, and an explicit boundary for vault numerics that must be supplied as resolved account inputs.
