"""compilers/stat_input_compiler.py - BACKWARD-COMPAT SHIM. Authority: qe.stat_input_compiler."""
from qe.stat_input_compiler import *  # noqa: F401, F403
from qe.stat_input_compiler import (
    compile_stat_inputs, _load_perk_entities, _load_perk_effects,
    PERK_TARGET_DESTINATION_OVERRIDES, TRADE_OFF_BENEFIT_EFFECT_INDEXES,
)  # noqa: F401
