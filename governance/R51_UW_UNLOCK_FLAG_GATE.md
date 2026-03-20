# R51 UW unlock flag gate

Applied a stat-engine unlock gate for `mechanic_param::uw.*` surfaces.

## Rule
If `capability::uw.<weapon>.owned` resolves to `False`, all `mechanic_param::uw.<weapon>.*` rows resolve to `0.0` with an explicit unlock-gated note.

## Compiler support
`compilers/stat_input_compiler.py` now emits one ownership capability row per ultimate weapon using the IDS `unlocked` flag.

## Scope
This is a state-engine guard, not a semantic rename pass. No Chrono Jump rename was performed here.
