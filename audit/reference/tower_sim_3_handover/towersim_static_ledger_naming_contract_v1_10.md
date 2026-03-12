
# TowerSim Static Contributor Ledger Naming Contract v1.10

## 1. Purpose

This contract defines the naming, schema, and normalization rules for the TowerSim v1 static contributor ledger.

The ledger is **contributor-centric**.

Each row represents:

- one direct contributor  
- from one contributor family  
- affecting one target stat  

This contract exists to make the ledger:

- deterministic
- auditable
- contributor-first
- stable across iterations
- usable by both humans and code

This is **not**:

- a combat formula specification
- a runtime event model
- a wave simulation spec
- a byte-for-byte archive of the build history

It is the **naming and schema contract for the active v1 ledger**.

---

# 2. Core principles

## 2.1 Contributor-centric, not stat-centric

The ledger is **not a list of stats**.  
It is a list of **contributors**.

A stat may have many contributors.  
Each contributor gets its own row.

## 2.2 One row = one contributor → one target stat

This is the canonical row rule.

If a source item affects multiple target stats, it must be split into multiple rows.

Examples:

- a single perk with two effects becomes two rows
- a trade-off perk with three effects becomes three rows
- a multi-output enhancement becomes multiple rows

## 2.3 target_stat is canonical

The canonical output column is:

`target_stat`

Older ideas like `resolved_property` are not part of the active schema.

## 2.4 contributor_id is stable

`contributor_id` is the stable identifier for a contributor row.

It should remain stable unless the contributor identity itself is redefined.

## 2.5 Derived-target contributors stay in the master ledger

A contributor can target a **derived stat** and still be a valid direct contributor.

Examples:

- wall health ratio contributors
- wall regen ratio contributors
- wall thorns ratio contributors

These rows remain in the master ledger.

Derived-target rows may be split into a convenience view, but they are **not removed from the canonical ledger**.

## 2.6 Explicit operation beats name inference

Names help readability.

But engine behavior must use:

- `operation`
- `semantic_type`
- `target_stat`

Do **not infer math only from string suffixes**.

---

# 3. Canonical row concept

Every active row in the ledger should answer:

- what contributor is this?
- which family does it belong to?
- what state controls it?
- what target stat does it affect?
- what operation does it apply?
- how certain are we?

---

# 4. Active contributor families

Allowed contributor families in the active v1 ledger:

- workshop
- enhancement
- lab
- card
- relic
- module_main
- module_sub
- module_unique
- perk
- bot
- uw
- uw_plus
- battle_condition
- guardian

No other source family should be added casually.

---

# 5. Naming layers

The ledger distinguishes three concepts:

- progression state
- contributor identity/output
- target stat

## 5.1 Progression state fields

State fields describe progression, unlock, equip, or gating state.

Pattern:

```
<source_family>__<track>__<state_kind>
```

Examples:

```
workshop__health__level
lab__health__level
card__health__level
uw__black_hole_size__level
bot__flame_damage__level
relic__ancient_tome__owned
card__damage__equipped
```

## 5.2 Contributor identifiers

Contributor identifiers describe the contributor itself.

Pattern:

```
<source_family>__<property_or_track>__<semantic_suffix>
```

Examples:

```
workshop__health__base
lab__health__bonus
card__health__multiplier
module_sub__defense_percent__pct_bonus
uw__black_hole_duration__duration_seconds
perk__damage__multiplier
```

## 5.3 Target stats

Target stats are canonical destination fields.

Examples:

```
health
critical_factor
free_attack_upgrade_chance
black_hole_duration_seconds
wall_regen
death_wave_effect_wave_quantity
```

---

# 6. State-field grammar

## 6.1 Allowed state kinds

Use the smallest honest set:

- level
- max_level
- owned
- equipped
- enabled
- unlocked
- tier
- rarity
- slots

Not every source uses every state kind.

## 6.2 State-field examples

```
workshop__damage__level
workshop__damage__max_level
lab__attack_speed__level
card__health__level
card__health__equipped
relic__space_sundial__owned
module_main__cannon__rarity
guardian__chip_slots__slots
```

## 6.3 Meaning of key state fields

- **level**: current progression level  
- **max_level**: current allowed maximum  
- **owned**: passive ownership gate  
- **equipped**: active equip gate  
- **enabled**: active feature gate  
- **unlocked**: unlock state  
- **tier**: source-tier state when relevant  
- **rarity**: rarity-driven state for modules and similar systems  
- **slots**: slot count state  

---

# 7. Contributor ID grammar

## 7.1 General pattern

Use:

```
<source_family>__<thing>__<semantic_suffix>
```

The middle section should be the contributor concept or track identity that most directly maps to the source mechanic.

## 7.2 Stable-ID rule

Once a `contributor_id` exists in the active ledger, **do not rename it casually**.

Rename only if:

- it is materially wrong
- it misrepresents the contributor identity
- it causes collisions or ambiguity

---

# 8. Semantic types

Allowed `semantic_type` values include:

- base
- multiplier
- pct
- pct_bonus
- chance
- chance_bonus
- ratio
- count
- count_bonus
- range_m
- range_m_bonus
- duration_seconds
- duration_seconds_bonus
- cooldown_seconds
- cooldown_seconds_reduction
- interval_seconds_reduction
- enabled
- cap
- angle_degrees
- rotation_rate
- scalar_bonus

These describe the **shape of the contributor**, not the engine behavior.

---

# 9. Operations

Allowed `operation` values:

- set_base
- multiply
- set_pct
- add_pct
- set_chance
- add_chance
- apply_ratio
- set_count
- add_count
- set_range_m
- add_range_m
- set_duration_seconds
- add_duration_seconds
- set_cooldown_seconds
- reduce_cooldown_seconds
- reduce_interval_seconds
- set_enabled
- apply_cap
- set_angle_degrees
- set_rotation_rate
- add_scalar

Important rule:

`review_required` is **not a valid operation**.

Placeholder operations are not allowed.

---

# 10. Semantic type vs operation mapping

| semantic_type | typical operation |
|---|---|
| base | set_base |
| multiplier | multiply |
| pct | set_pct |
| pct_bonus | add_pct |
| chance | set_chance |
| chance_bonus | add_chance |
| ratio | apply_ratio |
| count | set_count |
| count_bonus | add_count |
| range_m | set_range_m |
| range_m_bonus | add_range_m |
| duration_seconds | set_duration_seconds |
| duration_seconds_bonus | add_duration_seconds |
| cooldown_seconds | set_cooldown_seconds |
| cooldown_seconds_reduction | reduce_cooldown_seconds |
| interval_seconds_reduction | reduce_interval_seconds |
| enabled | set_enabled |
| cap | apply_cap |
| angle_degrees | set_angle_degrees |
| rotation_rate | set_rotation_rate |
| scalar_bonus | add_scalar |

If a specific contributor requires a different operation to stay truthful, **operation wins**.

---

# 11. Canonical schema

Active master ledger columns:

- ledger_scope
- source_family
- wiki_track_name
- source_item
- wiki_page_title
- wiki_page_url
- state_field
- max_level_field
- activation_field
- contributor_id
- semantic_type
- operation
- target_stat
- raw_or_derived
- dependencies
- unlock_notes
- wiki_semantic_note
- confidence
- uncertainty_notes
- source_ref

---

# 12. Column definitions

### ledger_scope
Build/integration grouping label.

### source_family
Contributor family.

### wiki_track_name
Mechanic name from the wiki.

### source_item
Source item being modeled.

Examples include:

- workshop tracks
- labs
- cards
- perks
- chips
- module effects

### wiki_page_title
Wiki page title used for sourcing.

### wiki_page_url
URL used for sourcing.

### state_field
Primary progression/gating field.

### max_level_field
Maximum progression field where relevant.

### activation_field
Equip/activation gate.

### contributor_id
Stable contributor identifier.

### semantic_type
Shape of the contributor value.

### operation
Explicit engine action.

### target_stat
Canonical destination stat.

### raw_or_derived

Allowed values:

- raw
- derived

### dependencies
Stats or gates required for interpretation.

### unlock_notes
Unlock or gating notes.

### wiki_semantic_note
Short interpretation note tied to wiki semantics.

### confidence

Allowed values:

- strong
- medium

### uncertainty_notes
Explicit unresolved details.

### source_ref
Human-readable provenance reference.

---

# 13. Columns removed from active use

Removed columns:

- duplicate family column
- duplicate contributor-field column
- constant field-kind column
- constant v1-static-scope column

Reason: redundant noise.

---

# 14. Confidence rules

### strong

Use when:

- contributor identity is pinned
- target stat is pinned
- operation is pinned
- numeric meaning is materially supported

### medium

Use when:

- contributor identity is real
- but an important value/curve detail remains unresolved

### weak

Avoid in active output.

---

# 15. Derived-target rule

Derived-target contributors remain in the canonical ledger.

Examples:

- wall health contributors
- wall regen ratio contributors
- wall thorns ratio contributors

Reason: they are still **direct contributors**.

---

# 16. Split-view rule

Split views may exist for convenience:

- base-target view
- derived-target view

These are **filters only**.

The master ledger remains canonical.

---

# 17. Multi-effect source-item rule

If a source item affects multiple target stats, split it into multiple rows.

Examples:

- trade-off perks
- multi-output enhancements
- battle conditions with multiple stat effects
- cards or perks with several direct effects

This preserves the one-row rule.

---

# 18. Source-family-specific guidance

## 18.1 Workshop
Use direct workshop track identity.

## 18.2 Enhancement
Enhancement is a separate family from workshop.

## 18.3 Lab
Labs may:

- scale workshop increments
- add bonuses
- unlock capabilities
- reduce cooldowns
- add durations or counts

## 18.4 Card
Cards often require:

- level
- equipped activation field

## 18.5 Relic
Relics are modeled at **simulation-meaningful aggregation level**, not collectible level.

## 18.6 Module families
Keep separate:

- module_main
- module_sub
- module_unique

## 18.7 UW vs UW+
Keep separate:

- uw
- uw_plus

## 18.8 Perk
Perks are a contributor family.

## 18.9 Battle condition
Battle conditions are a contributor family.

## 18.10 Guardian
Guardian is a contributor family modeled at chip parameter level.

---

# 19. Target-stat rules

## 19.1 Canonical naming
`target_stat` names should remain stable.

## 19.2 Safe normalization

Examples already normalized:

```
crit_chance → critical_chance
crit_factor → critical_factor
super_crit_mult → super_crit_multiplier
free_attack_upgrade → free_attack_upgrade_chance
free_defense_upgrade → free_defense_upgrade_chance
free_utility_upgrade → free_utility_upgrade_chance
```

## 19.3 Do not force speculative renames

If renaming depends on unresolved combat-model semantics, **do not force it**.

---

# 20. Derived vs raw targets

## Raw targets

Examples:

- health
- damage
- critical_factor
- golden_tower_duration_seconds

## Derived targets

Examples:

- wall_regen
- wall_thorns
- wall_health

Classification is carried by `raw_or_derived`.

---

# 21. Governance rules for future edits

### 21.1 Do not add rows casually
Every row must have a defendable source basis.

### 21.2 Do not infer mechanics from vague snippets

### 21.3 Do not use placeholder operations

### 21.4 Avoid duplicated meaning across columns

### 21.5 Do not remove derived-target contributors

### 21.6 Do not silently promote medium-confidence rows

### 21.7 Keep contributor_id stable

---

# 22. Known unresolved block in v1.10

Remaining unresolved value curves:

- module_main__damage__multiplier
- module_main__health__multiplier
- module_main__coin_bonus__multiplier
- module_main__ultimate_weapon_damage__multiplier

These remain **medium confidence**.

---

# 23. Examples

### Example A — workshop base scalar

```
state_field: workshop__health__level
max_level_field: workshop__health__max_level
contributor_id: workshop__health__base
semantic_type: base
operation: set_base
target_stat: health
```

### Example B — lab additive percent

```
state_field: lab__defense_percent__level
contributor_id: lab__defense_percent__pct_bonus
semantic_type: pct_bonus
operation: add_pct
target_stat: defense_percent
```

### Example C — card multiplier with activation

```
state_field: card__health__level
activation_field: card__health__equipped
contributor_id: card__health__multiplier
semantic_type: multiplier
operation: multiply
target_stat: health
```

### Example D — derived-target ratio

```
state_field: lab__wall_regen__level
contributor_id: lab__wall_regen__ratio
semantic_type: ratio
operation: apply_ratio
target_stat: wall_regen
raw_or_derived: derived
```

### Example E — cooldown reduction

```
state_field: lab__golden_bot_cooldown__level
contributor_id: lab__golden_bot_cooldown__cooldown_seconds_reduction
semantic_type: cooldown_seconds_reduction
operation: reduce_cooldown_seconds
target_stat: golden_bot_cooldown_seconds
```

### Example F — enable-style contributor

```
state_field: lab__missile_barrage__level
contributor_id: lab__missile_barrage__enabled
semantic_type: enabled
operation: set_enabled
target_stat: missile_barrage_enabled
```

---

# 24. Final rule

If a naming or schema choice is:

- neat
- compact
- elegant

but **not truthful to the contributor semantics**,

then **truth wins**.

Pretty lies are still lies.

The ledger should prefer **precise ugliness over elegant nonsense**.
