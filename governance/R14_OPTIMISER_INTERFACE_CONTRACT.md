# R14 Optimiser Interface Contract

## Decision
The optimiser should consume calculator outputs through an explicit multi-plane interface.

### Plane order
1. `canonical`
2. `runtime_mechanic`
3. `helper_optimizer`

### Guarantees by plane
| Plane | Intended use | Guarantee now | Notes |
|---|---|---|---|
| canonical | core objective inputs and constraints | highest | publishable rows, primary decision inputs |
| runtime_mechanic | mechanic parameters that shape simulation and constraints | medium-high | resolved params, not all are strategy helpers |
| helper_optimizer | derived strategic/econ/helper rows | medium | useful, emitted deliberately, must remain clearly non-canonical |

### Consumer rule
The optimiser may consume:
- canonical rows by default
- runtime/helper rows only when explicitly whitelisted in the optimiser interface ledger

It must **not** infer calculator canon from helper rows.

### Near-term optimiser seed set
The first trusted optimiser-facing set should include:
- survivability core: `tower_hp`, `tower_regen`
- damage core: `tower_damage`
- econ core: `coin_kill_multiplier`, `cash_kill_multiplier`
- helper rows: Plasma Cannon effect, BH/DW/SL coin bonus multipliers

### Why now
The helper plane is now live in emitted output, so the optimiser can move from abstract downstream consumer to contract-based consumer.
