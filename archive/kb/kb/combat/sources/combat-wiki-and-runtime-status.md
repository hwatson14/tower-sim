# Combat Wiki and Runtime Status

## Closed enough for KB use
- Defense ordering is materially closed for Defense Percent, Defense Absolute, and the post-Defense-Absolute separate DR bundle.
- Key contact routing is materially closed for wall-first routing, HP loss before thorns, and same-contact damage plus thorn resolution.
- Evidence tiers are mandatory: `public_source` and `user_observed` are not interchangeable.

## Low-materiality boundary nuance
- Same-tick tie-break precedence between simultaneous damage/effect sources is intentionally de-scoped.
- Expiry-precedence edges when a timed effect ends on the same moment another event resolves are intentionally de-scoped.
- Boss Orb Boss Hit same-moment precedence versus other damage is intentionally de-scoped.
- Boss hit interval is fixed at 2.0 seconds as an accepted user model constant.

## Use rule
For KB and AI retrieval, treat the runtime-ordering ledger and canonical ordering file as the first surfaces.
Use the pipeline file for staged flow.
Use the boundary note only when a task explicitly asks for frame-exact simulation semantics.

## Current closure status
- Material defense and contact ordering is closed for practical KB use.
- Boss hit interval is fixed at 2.0 seconds as an accepted user model constant.
- Same-tick and expiry micro-precedence are intentionally de-scoped as low-materiality nuance rather than treated as active blockers.
