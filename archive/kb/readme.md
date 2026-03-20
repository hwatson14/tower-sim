# Tower KB

Curated AI-facing Tower knowledge base for ChatGPT lookup, mechanics reasoning, theorycraft support, strategy support, and simulator work for the intended simulator scope.

## Start here
1. `START_HERE_FOR_AI.md`
2. `CHATGPT_KB_PROFILE.yaml`
3. `KNOWLEDGE_ROLE_SCHEMA.yaml`
4. `KNOWLEDGE_ROLE_REGISTRY.csv`
5. `manifest.json`
6. `RETRIEVAL_POLICY.yaml`
7. `TASK_ENTRYPOINTS.yaml`
8. `kb/index.md`

## What this package is
- A curated truth package for ChatGPT, not a development workspace
- Canonical tables and contracts first for mechanics
- Explicit boundaries instead of invented exactness
- Strategy guidance and community signal retained for theorycraft and practical advice
- Suitable for practical deterministic modelling under the intended sim scope

## What this package is not
- A changelog archive
- A validation workspace
- A frame-exact replay simulator
- A community-rumour dump presented as mechanics canon

## Knowledge layers
- `kb/**/tables/**` → canonical mechanics
- `kb/**/contracts/**` → canonical contracts
- `kb/community/**` → community signal
- `kb/advisory/**` → strategy and reasoning guidance
- `kb/**/notes/**` → explanatory secondary material
- `kb/**/sources/**` → provenance grounding
- `kb/**/derived/**` → derived non-primary material

## Core boundary files
- `UNKNOWNS_OPERATING_POLICY.csv`
- `kb/ledgers/tables/simulator-scope-boundary-ledger.csv`
- `kb/ledgers/tables/scope-boundary-registry.csv`
