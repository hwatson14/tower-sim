# Naming grammar

## Why this exists
The KB needs one machine-facing grammar that can survive naming churn across the wiki, Effective Paths, repo extracts, and user shorthand.

## Canonical split
Use four different naming layers deliberately:

1. **Canonical stat ids**
   - Stable engine-facing outputs such as `tower_hp`, `wall_hp`, `tower_range_m`.
   - These are what evaluators should read.

2. **Runtime mechanic parameter ids**
   - Dotted paths for mechanics that are not ordinary permanent stats, such as `uw.black_hole.duration_seconds` or `bot.golden.cooldown_seconds`.
   - These belong to mechanic execution rather than the generic stat surface.

3. **Contributor ids**
   - Four-part grammar: `source_section__entity_section__attribute_section__metric_section`
   - Example: `lab__tower__attack_speed__pct`
   - This preserves provenance without polluting canonical stat ids.

4. **Aliases**
   - Retrieval-only names such as `BH`, `GT`, `EALS`, and `Workshop Plus`.
   - Aliases should help search, not create competing truths.

## The goblin to avoid
Do not treat everything as one species of object called a stat.
A permanent tower stat, a mechanic runtime parameter, a capability flag, and a source-side contributor are different beasts wearing similar hats.

## Canonical terminology rule
- Use **Enhancements** as the KB-wide canonical term.
- Preserve **Workshop Enhancement** only when mirroring wiki page names or raw source wording.
- Preserve **Workshop Plus** only as an alias.
