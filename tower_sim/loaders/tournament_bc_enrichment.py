from __future__ import annotations

from typing import Dict, Iterable, Tuple


# Provenance: tables/heat_bc_registry.csv + tables/heat_scale_long.csv
# via canonical tournament heat/BC integration (see tests asserting CSV order parity).
TOURNAMENT_HEAT_BC_IDS: Tuple[str, ...] = (
    "death_ray_resistance:",
    "knockback_resistance:",
    "orb_resistance:",
    "plasma_cannon_resistance:",
    "thorns_resistance:",
)


TOURNAMENT_HEAT_BC_TO_STATS: Dict[str, Tuple[str, ...]] = {
    "orb_resistance:": ("orb_damage_mult",),
    "death_ray_resistance:": ("death_ray_damage_mult",),
    "thorns_resistance:": ("thorns_damage_mult",),
    "plasma_cannon_resistance:": ("plasma_cannon_damage_mult",),
    "knockback_resistance:": ("knockback_mult",),
}


def map_tournament_heat_bc_to_stat_magnitudes(
    *,
    registry,
    bc_values: Dict[str, float],
    bc_ids: Iterable[str] = TOURNAMENT_HEAT_BC_IDS,
) -> Dict[str, float]:
    magnitudes: Dict[str, float] = {}
    for bc_id in bc_ids:
        if bc_id not in bc_values:
            continue
        value = float(bc_values[bc_id])
        for stat_id in TOURNAMENT_HEAT_BC_TO_STATS[bc_id]:
            registry.validate_stat_id(stat_id)
            magnitudes[stat_id] = value
    return magnitudes


__all__ = [
    "TOURNAMENT_HEAT_BC_IDS",
    "TOURNAMENT_HEAT_BC_TO_STATS",
    "map_tournament_heat_bc_to_stat_magnitudes",
]
