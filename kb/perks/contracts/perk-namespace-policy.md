# Perk namespace policy

Canonical perk flows use exactly one canonical preset from the repo preset contract: `Tourney`, `Farming`, `Milestone`, `Preset 4`, or `Preset 5`.

Transient non-canonical perk preset names are allowed only when they are explicitly typed with `preset_namespace_class: transient` in the perk config or in-memory account-state mutation. These transient names are runtime-only scaffolding for generated/timeline perk states and must not become canonical preset truth.

Contract rules:
- canonical flows fail closed on non-canonical perk preset names
- canonical flows resolve one selected perk preset only; they must not merge requested, active, and hidden default preset keys
- transient perk preset namespaces remain isolated from canonical preset truth and must be surfaced as transient whenever they are intentionally created
