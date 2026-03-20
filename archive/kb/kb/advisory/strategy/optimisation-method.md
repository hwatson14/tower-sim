# Optimisation Evaluation Method
Version: phase4_v1
Layer: 4 — Optimisation Framework
Status: Refactored

## Purpose
Define the reusable method for evaluating farming and tournament choices without collapsing into generic meta advice.

## Core method
Use a 4-layer evaluation stack.

### Layer A — Main-slot unique effect
Question:
What does the full-strength unique effect do for the objective?

### Layer B — Assist-slot value
Question:
What does the weaker assist version contribute, and is assist even unlocked?

### Layer C — Visible substats
Question:
What value comes from the actual substats on the module, not a theoretical perfect roll?

### Layer D — Build fit
Question:
How does the package fit the actual build shell?

Examples of build-fit dimensions:
- PBH / BH-centric survivability
- controlled farming kill timing
- wall / regen envelope
- boss throughput
- control interactions

## Method rules
1. Start from the objective function.
2. Do not optimise farming as raw DPS.
3. Do not assume the generic “best module” is best for this account.
4. Separate unique-effect value from substat-stick value.
5. Read slot locks and assist unlocks before recommending pairings.
6. Treat current measured presets as stronger evidence than generic heuristics.

## Evidence hierarchy
Highest to lowest:
1. verified mechanics
2. measured account results
3. structured comparative reasoning
4. generic community heuristics

## Output rule
Every recommendation should state:
- objective
- options considered
- why the recommendation wins
- what could falsify the recommendation
