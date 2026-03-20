# Economy currency contract

## Domain ownership
Economy owns resource identity, persistence, acquisition channel summary, and primary spend sink.

## Surface semantics
- `currency-summary.csv`: canonical identity table for currencies and resource buckets.
- `vault-overview.csv`: canonical high-level structure for Vault gating and tech-tree ownership.
- `economy-resource-flows.csv`: normalized bridge table linking resource -> source channel -> primary sink.

## Interpretation rules
- Do not treat all economy objects as fungible. Currencies are not interchangeable just because they all increase progression.
- A resource can have more than one source or sink; the flow table captures the dominant current role, not every edge case.
- Detailed per-level ladders live in owning domains when a system owns the ladder. Example: bot medal ladders live in `bots`, not `economy`.

## Confidence rule
High-level economy identity and Vault gating are wiki-backed. Fine-grained ladders remain distributed across owning domains.
