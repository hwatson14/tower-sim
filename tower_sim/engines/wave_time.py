
from __future__ import annotations

from tower_sim.libs.cards_lib import card_value, load_cards_tables
from tower_sim.util.account_snapshot import AccountSnapshot

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


def active_preset_name(*, run_type: str, snapshot: AccountSnapshot) -> str:
    mode_value = getattr(run_type, "value", run_type)
    run_key = str(mode_value).lower().strip()
    if run_key == "tournament":
        return "Tourney"
    if run_key == "farming":
        return "Farming"
    return snapshot.default_preset


def wa_reduction_from_snapshot(*, snapshot: AccountSnapshot, run_type: str) -> float:
    preset_name = active_preset_name(run_type=run_type, snapshot=snapshot)
    preset_cards = snapshot.card_presets.get(preset_name)
    if preset_cards is None:
        raise ValueError(f"Missing card preset {preset_name!r} on snapshot.")
    if "Wave Accelerator" not in preset_cards:
        return 0.0

    wa_card = snapshot.cards_inventory.get("Wave Accelerator")
    if wa_card is None:
        raise ValueError("Wave Accelerator equipped but not present in cards inventory.")
    if wa_card.level is None:
        raise ValueError("Wave Accelerator equipped but card level is missing.")

    tables = load_cards_tables()
    raw_value = card_value("Wave Accelerator", wa_card.level, tables)
    normalized = raw_value.strip()
    if not normalized.endswith("%"):
        raise ValueError(f"Unexpected Wave Accelerator value format: {raw_value!r}")
    return float(normalized.rstrip("%")) / 100.0
