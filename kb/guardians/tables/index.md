# Guardians tables index

Guardian primary canon now separates:
- exact linear value tracks in `kb/formulas/tables/canonical-formula-registry.csv`
- irregular bit-cost-bearing row tables here in `kb/guardians/tables/`

## Primary active tables
- `guardian-chip-baselines.csv`
- `guardian-upgrades.csv`
- `wiki-verified-guardian-ally-upgrades.csv`
- `wiki-verified-guardian-attack-upgrades.csv`
- `wiki-verified-guardian-bounty-upgrades.csv`
- `wiki-verified-guardian-fetch-upgrades.csv`
- `wiki-verified-guardian-summon-upgrades.csv`
- `wiki-verified-guardian-scout-upgrades.csv`
- `wiki-verified-guardian-scout-summary.csv`

## Notes
These row tables are retained as primary canon because the bit-cost columns are irregular and source-primary, so formula-only storage would lose canonical upgrade-cost information.


- See derived/materialized or registry files for non-primary aggregate or bundle-backed surfaces.

- wiki-verified-guardian-bounty-summary.csv
- wiki-verified-guardian-summon-summary.csv

- wiki-verified-guardian-ally-summary.csv
- wiki-verified-guardian-attack-summary.csv
- wiki-verified-guardian-fetch-summary.csv

- wiki-verified-guardian-unlock-and-slots-summary.csv