# Namespace hygiene

Canonical output artifacts must publish only canonical preset names: `Tourney`, `Farming`, `Milestone`, `Preset 4`, and `Preset 5`.

Transient preset namespaces are permitted only for explicitly typed runtime scaffolding such as projected-max perk generation, progression timeline snapshots, and full-perk audit helpers. Those transient names must be quarantined behind transient typing and must not leak into canonical artifact families or canonical identity.

Rules:
- canonical/publishable artifacts sanitize transient perk preset names back to the canonical preset context they were resolved under
- transient preset names may exist only on explicit transient inputs or in-memory runtime helpers
- state identity fingerprints transient perk content and namespace class, but not the raw transient namespace string as if it were canonical preset identity
- explicit transient sources remain discoverable through their dedicated input/runtime files rather than through canonical published artifacts
