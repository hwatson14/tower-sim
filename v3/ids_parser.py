"""v3 Phase-1 IDS parser surface.

This module intentionally re-exports the validated parser from the existing
TowerSim core so v3 can consume the same deterministic, fail-closed behavior
without forking parser logic during bootstrap.
"""

from tower_sim.loaders.ids_parser import (  # noqa: F401
    DEFAULT_IDS_PATHS,
    SECTION_SPECS,
    SectionSpec,
    parse_ids,
    resolve_ids_path,
)
