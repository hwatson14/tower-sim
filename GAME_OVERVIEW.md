# Game Overview — *The Tower: Idle Tower Defense*

This document provides a **high-level, system-oriented overview** of the mobile game  
**The Tower — Idle Tower Defense**.

Its purpose is to describe:

- what game systems exist  
- how those systems interact conceptually  
- what kinds of player decisions and progression matter  

This document **intentionally avoids**:

- numeric values  
- balance judgments  
- simulator-specific assumptions  
- implementation details  

Those belong in authoritative tables, architecture documents, or project intent files.

---

## 1. Core gameplay loop

At its core, *The Tower* is a wave-based survival game.

- Enemies spawn in discrete waves.
- The player controls a stationary tower.
- Enemy strength increases as waves progress.
- A run ends when the tower can no longer survive incoming damage.

The fundamental question the game asks is:

> **How far can this tower configuration survive as enemy strength scales?**

This is the question TowerSim ultimately answers.

---

## 2. Waves, tiers, and progression

### Waves
- The game progresses in numbered waves.
- Enemy health and damage scale as a function of wave index.
- Certain mechanics trigger at specific waves or intervals (e.g. bosses, perks, milestones).

### Tiers
- Tiers represent distinct difficulty bands.
- Higher tiers begin with stronger enemies and/or faster scaling.
- Tier selection fundamentally reshapes survivability outcomes.

---

## 3. Enemy model (conceptual)

Enemies are characterized by:

- health  
- attack damage  
- spawn cadence  
- special classifications (e.g. bosses, elites, fleets)

From a modeling perspective:

- enemy strength is primarily a function of **tier × wave**
- additional global modifiers may apply (battle conditions, heat, research effects)

The exact combat resolution is not exposed to the player and is **assumed deterministic** once inputs are fixed.

---

## 4. Tower survivability

Tower survivability emerges from the interaction of multiple systems.

Some systems provide **time-based defensive, offensive, or crowd-control windows** driven by cooldown-based effects.  
While these systems are deterministic, their **phase alignment relative to enemy actions may not be observable**, introducing bounded outcome variability.

### 4.1 Defensive stats

Defensive capability includes, but is not limited to:

- Health  
- Regeneration  
- Defense  
- Damage Reduction  
- Absolute defense (flat mitigation)

These determine how much damage the tower can absorb over time.

### 4.2 Damage output (offensive capability)

Although survival ends a run, **damage output determines how long enemies are allowed to deal damage**.

Damage systems improve survivability indirectly by:

- reducing enemy count  
- killing enemies before contact  
- shortening exposure time to high-damage waves  
- controlling boss and elite pressure  

Damage in *The Tower* is not a single stat.

#### Sources of damage
Damage may originate from:

- tower projectiles  
- damage-over-time effects  
- percentage-based health damage  
- triggered effects from cards, modules, or ultimate weapons  
- passive systems (e.g. orbitals, fields, pulses)

Some sources scale with enemy health, others with tower stats, and others are fixed or capped.

#### Damage is conditional, not continuous
Damage effectiveness depends on:

- enemy density  
- targeting rules  
- hit cadence  
- cooldown alignment  
- whether enemies are grouped, delayed, or controlled  

As a result, damage cannot be meaningfully reduced to a single “DPS” value without context.

---

## 5. Crowd control (CC) and battlefield control

Crowd control systems are a core pillar of late-game performance.

Rather than directly reducing enemy stats, CC systems **alter when and how enemies are able to deal damage**, reshaping the battlefield.

### Types of crowd control

Conceptual CC categories include:

- **Slow / speed reduction**  
  Enemies take longer to reach the tower.

- **Stun / freeze / immobilization**  
  Enemies are temporarily unable to act.

- **Knockback / displacement**  
  Enemy position relative to the tower is altered.

- **Grouping / pulling**  
  Enemies are clustered to enable burst or area damage.

- **Spawn or wave pacing modifiers**  
  Enemy arrival timing changes without altering individual stats.

### CC as time dilation

Conceptually, CC acts as *time dilation*:

- enemies exist for longer  
- damage windows shift  
- cooldown-based defenses gain more overlap  

This is why CC often multiplies the effectiveness of:

- damage reduction windows  
- regeneration  
- cooldown-driven defensive systems  
- burst or AoE damage  

### CC determinism and phase sensitivity

CC activation is deterministic, but:

- its alignment relative to enemy actions may not be observable  
- outcomes vary within bounded envelopes  

This makes CC a major contributor to best-case and worst-case survivability envelopes.

---

## 6. Player progression systems

The game contains multiple progression layers that modify tower stats or behavior.

Most progression systems affect multiple domains simultaneously:

- survivability  
- damage output  
- crowd control  
- timing alignment between systems  

**These interactions are often more important than the magnitude of any single stat.**

### 6.1 Labs
- Long-term, time-based research upgrades.
- Affect tower stats, enemy stats, bots, and ultimate weapons.
- Persistent across runs.

### 6.2 Workshop
- Run-independent upgrades purchased with coins.
- Typically linear or capped stat improvements.
- Persistent across runs.

### 6.3 Cards
- Slottable modifiers with levels.
- Provide stat bonuses or special effects.
- Loadout-limited.

### 6.4 Ultimate Weapons (UW)
- Powerful cooldown-based systems.
- Multiple upgradeable stats.
- Often define late-game survivability.
- May include active and passive effects.

### 6.5 Modules
- Equipment-like items with fixed slots.
- Provide primary stats, unique effects, and substats.
- Rarity and enhancement significantly affect outcomes.

### 6.6 Bots
- Autonomous helpers with upgradeable tracks.
- Provide offensive, defensive, or utility effects.
- Often operate on cooldown cycles.

### 6.7 Guardians and chips
- Triggered or cooldown-based effects.
- Often interact with timing, targeting, or mitigation.

### 6.8 Relics and themes
- Persistent bonuses unlocked via progression.
- Provide global or conditional stat effects.

---

## 7. Perks (run-specific variability)

Perks are temporary upgrades offered during a run.

Key properties:

- Effects are deterministic once selected.
- Offer order is random.
- Acquisition timing matters.

Perks are one of the few sources of run-to-run variability in the game.

---

## 8. Damage, CC, and survivability as a system

Late-game outcomes are driven by the interaction of three envelopes:

- **Enemy damage envelope** (wave scaling)  
- **Player survivability envelope** (health, regen, DR)  
- **Enemy exposure envelope** (damage + CC)  

A tower may survive longer by:

- tanking more damage  
- reducing damage taken  
- killing enemies faster  
- preventing enemies from dealing damage at all  

All four strategies coexist and compound.

Additional global modifiers include:

### Enemy Level Skip (ELS)
- Reduces effective enemy scaling by skipping levels.
- Exists in separate forms (e.g. attack vs health).

### Battle Conditions
- Global rule modifiers.
- Especially relevant in tournaments.

### Heat
- Tournament-specific scaling that increases difficulty over time.

---

## 9. Game modes (conceptual)

The same systems operate under different constraints:

### Milestone / progression runs
- Tier-based progression.
- Perks enabled.
- Goal: unlock content and push waves.

### Tournament runs
- Fixed rule sets.
- Battle conditions and heat applied.
- Perks often disabled.
- Competitive outcomes.

### Farming runs
- Optimized for resource gain.
- Economic considerations dominate (not modeled in v1).

---

## 10. Why this matters for TowerSim

TowerSim does not attempt to recreate full runtime behavior.

Instead, it:

- treats these systems as inputs to survivability  
- models only what is required to answer specific questions  
- refuses to guess when data is missing  

Understanding what systems exist — even if not yet modeled — is essential to:

- avoid silent omissions  
- correctly scope simulation versions  
- prevent accidental invention of mechanics  

---

## 11. Relationship to other documents

This document answers:

**“What exists in the game?”**

Related documents answer:

- **Why TowerSim exists and what it computes** → `PROJECT_INTENT.md`  
- **How the simulator is structured** → `ARCHITECTURE.md`  
- **What data is authoritative** → `tables/README.md`  
- **What structure is enforced** → `REPO_MAP.yaml`  

This separation is deliberate.
