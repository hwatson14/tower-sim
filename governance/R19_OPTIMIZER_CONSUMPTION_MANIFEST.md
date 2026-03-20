# R19 Optimizer Consumption Manifest

## Purpose
This artifact turns the R18 objective-family payloads into a strict downstream consumption contract.

## Rail guard
- Calculator baseline remains source of truth.
- EP defines the core objective family framing: `eecon`, `ehp`, `edamage`.
- Harness remains the readiness/completeness judge.
- Optimizer consumes emitted payloads only and does not define canon.

## Global rules
- Consume only emitted payload artifacts, not the full statbook.
- Allowed planes: `canonical`, `runtime_mechanic`, `helper_optimizer`.
- Allowed status: `resolved` only.
- Allowed trust tiers: `tier1`, `tier2`.
- Missing payload file: fail closed for that objective family.
- Missing row inside an existing payload: skip row and record a gap.
- Unknown plane, unknown trust tier, unresolved row, or duplicate destination: exclude or fail closed as specified in the manifest JSON.

## Objective families

### eecon
- Rows: 22
- Planes: canonical|helper_optimizer|runtime_mechanic
- Trust tiers: tier1|tier2
- Domains: economy
- JSON: `output/optimizer_payload_r18_eecon.json`
- CSV: `output/optimizer_payload_r18_eecon.csv`

### ehp
- Rows: 5
- Planes: canonical|helper_optimizer|runtime_mechanic
- Trust tiers: tier1|tier2
- Domains: survivability
- JSON: `output/optimizer_payload_r18_ehp.json`
- CSV: `output/optimizer_payload_r18_ehp.csv`

### edamage
- Rows: 4
- Planes: canonical|helper_optimizer|runtime_mechanic
- Trust tiers: tier1|tier2
- Domains: damage
- JSON: `output/optimizer_payload_r18_edamage.json`
- CSV: `output/optimizer_payload_r18_edamage.csv`

### survival
- Rows: 6
- Planes: canonical|helper_optimizer|runtime_mechanic
- Trust tiers: tier1|tier2
- Domains: boss_control|survivability
- JSON: `output/optimizer_payload_r18_survival.json`
- CSV: `output/optimizer_payload_r18_survival.csv`

## Required fields
- destination
- output_plane
- optimizer_domain
- trust_tier
- status
- value
- display_value
- unit_or_format
- resolver
- formula_class
- rationale

## Why this matters
The optimizer now has a precise execution contract. It can consume small trusted objective-family payloads without reading the entire calculator statbook and without redefining calculator canon.
