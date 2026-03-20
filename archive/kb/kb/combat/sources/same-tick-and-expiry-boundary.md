# Same-tick and expiry boundary note

## Purpose
This note fences the remaining low-materiality runtime nuance after the material-ordering patch.

## Closed for practical use
- Defense Percent applies before Defense Absolute.
- Separate post-Defense-Absolute damage reduction sources apply after Defense Absolute.
- Key contact routing rules are retained with explicit evidence tiers.
- Boss hit interval is fixed at 2.0s in the active model.

## Intentionally de-scoped
The KB does **not** try to canonize exact same-tick tie-breaks or expiry micro-precedence, because they are not currently material to practical tower evaluation or KB retrieval.

## Rule for AI consumers
Use the runtime-ordering ledger and canonical combat ordering surfaces for material logic.
Do not treat same-tick or expiry micro-order as a blocker unless a future task specifically requires frame-exact simulation semantics.
