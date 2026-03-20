# R16 Optimiser Payload Export

## Rail confirmation
This work remains on rails:
- calculator baseline is still the implementation truth source
- EP remains a validation and enrichment source
- harness remains the governance/completeness judge
- optimiser remains downstream only and consumes a whitelist contract

## What was produced
- `output/optimizer_payload_r16.json`
- `output/optimizer_payload_r16.csv`

## Contract scope
- Rows exported: 32
- Only rows already whitelisted in `governance/OPTIMISER_INTERFACE_LEDGER_R15.csv`
- Only rows with `status=resolved`
- Output planes preserved as distinct fields

## Plane counts
{
  "canonical": 5,
  "helper_optimizer": 12,
  "runtime_mechanic": 15
}

## Domain counts
{
  "survivability": 5,
  "damage": 4,
  "economy": 22,
  "boss_control": 1
}

## Trust tier counts
{
  "tier1": 9,
  "tier2": 23
}

## Notes
This iteration is a payload/export artifact only. It does not widen canon, change formulas, or alter emitted calculator rows. It converts the existing optimiser whitelist into a concrete downstream payload.
