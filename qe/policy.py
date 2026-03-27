"""
qe/policy.py — QE resolver policy constants.

These govern how the QE layer resolves computed values and are NOT
source-backed wiki/gameplay truth. They are engine resolution decisions.

Contrast with engine/kb_surfaces.py which holds source-backed gameplay constants.
"""

# Boss kill threshold: internal HP floor below which boss is considered dead.
# This is a QE resolution policy, not a wiki-sourced boss mechanic.
BOSS_KILL_HP_THRESHOLD: float = 1.0
