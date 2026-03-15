# START HERE FOR AI

This package is a **curated Tower knowledge base for ChatGPT**.

## Package claim
Use this KB for **simulator-complete reasoning for the intended sim scope**, **practical deterministic modelling**, and **strategy/theorycraft support**.
Do **not** treat it as exact-tick or frame-exact replay canon.

## First-pass loading order
1. `CHATGPT_KB_PROFILE.yaml`
2. `KNOWLEDGE_ROLE_SCHEMA.yaml`
3. `KNOWLEDGE_ROLE_REGISTRY.csv`
4. `manifest.json`
5. `RETRIEVAL_POLICY.yaml`
6. `TASK_ENTRYPOINTS.yaml`
7. `SURFACE_EXECUTION_ORDER.yaml`
8. `SURFACE_PRIORITY_REGISTRY.csv`
9. `MASTER_SURFACE_TRUST_LEDGER.csv`
10. `UNKNOWNS_OPERATING_POLICY.csv`
11. `kb/index.md`

## Core scope decisions
- Accept EP-verified module main-effect totals as **package canon** for this package.
- Accept vault numeric bonuses only through `kb/economy/tables/vault-externalized-simulator-inputs.csv` when explicit resolved account values are supplied.
- Apply the timing rule that thorns damage resolves immediately after incoming damage.
- Treat broader same-tick and frame-exact micro-precedence as **intentionally out of scope**.
- Treat the 17 tournament BC exact rows as an **accepted unknown-community boundary**.
- Use the canonical Wall Fortification unlock choice **Tier 14 / Wave 60**.

## Knowledge layers
- **Canonical mechanics:** `kb/**/tables/**`
- **Canonical contracts:** `kb/**/contracts/**`
- **Package canon / boundaries:** `UNKNOWNS_OPERATING_POLICY.csv`, `kb/ledgers/tables/simulator-scope-boundary-ledger.csv`, `kb/ledgers/tables/scope-boundary-registry.csv`, and explicit package-canon tables
- **Strategy guidance:** `kb/advisory/strategy/**` and `kb/advisory/reasoning/**`
- **Community signal:** `kb/community/**`

## Rules for ChatGPT
- Use canonical mechanics and contracts first for lookup and mechanics questions.
- Use strategy and community material for theorycraft, prioritization, diagnosis, and practical play advice.
- Never let strategy or community material override canonical mechanics or boundary policy.
- When a boundary file says `accepted_unknown_boundary` or `out_of_scope_tick_precedence`, report that directly and stop rather than inventing exactness.
