
from __future__ import annotations

# Wave timing model
#
# The wiki explicitly defines that Wave Accelerator reduces the "wave cooldown timer" (downtime between
# waves), i.e. the part of the wave when no enemies can spawn.
#
# The wiki does NOT provide a single canonical "total wave time" because it depends on build and wave
# conditions (spawn rate, kill speed, etc.). For simulation purposes we treat total wave time as:
#
#   wave_seconds = base_wave_active_seconds + wave_cooldown_seconds_after_WA
#
# where Wave Accelerator only reduces the cooldown component.
#
# Defaults below are **configurable** and should be treated as empirical placeholders until we lock a
# more authoritative source.

# Empirical defaults (can be overridden by user config)
DEFAULT_WAVE_ACTIVE_SECONDS_FARM = 35.0
DEFAULT_WAVE_ACTIVE_SECONDS_TOURNEY = 30.0

# Cooldown between waves (commonly cited as 9 seconds; WA reduces this component)
WAVE_COOLDOWN_SECONDS = 9.0

# Some tournaments appear to have a shorter cooldown; keep as a separate configurable multiplier.
TOURNEY_COOLDOWN_MULT = 0.5

# Galaxy Compressor reduction per package, by rarity (corrected)
GCOMP_SECONDS_BY_RARITY = {
    "Epic": 10.0,
    "Legendary": 13.0,
    "Mythic": 17.0,
    "Ancestral": 20.0,
}

def wave_seconds(wa_reduction: float, tournament: bool) -> float:
    """Return expected seconds per wave.

    Parameters
    - wa_reduction: fraction in [0, 1] representing WA % cooldown reduction.
    - tournament: whether the run is a tournament.

    Notes
    - WA only reduces the cooldown component (wiki).
    - Active wave time is treated as an input (empirical default).
    """
    wa_reduction = max(0.0, min(1.0, wa_reduction))
    active = DEFAULT_WAVE_ACTIVE_SECONDS_TOURNEY if tournament else DEFAULT_WAVE_ACTIVE_SECONDS_FARM
    cooldown = WAVE_COOLDOWN_SECONDS * (TOURNEY_COOLDOWN_MULT if tournament else 1.0)
    return active + cooldown * (1.0 - wa_reduction)
