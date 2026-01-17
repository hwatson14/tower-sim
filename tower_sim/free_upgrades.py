from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FreeUpgradeChances:
    """Free upgrade chances per workshop category.

    All fields are expressed as fractions (e.g. 0.495 for 49.5%).
    Chances may exceed 1.0 (100%) via multipliers; the engine will treat this
    as guaranteed additional upgrades plus a remainder probability.
    """

    attack: float
    defense: float
    utility: float


def expected_upgrades_per_trigger(chance: float) -> float:
    """Expected number of upgrades produced by a single trigger.

    Wiki rule: if free-upgrade chance is over 100%, there is a chance to get
    another upgrade.

    We interpret this as: each full 100% gives one guaranteed upgrade, plus
    the fractional remainder gives a probabilistic extra upgrade.
    """
    if chance <= 0:
        return 0.0
    guaranteed = int(chance)  # e.g. 2.3 -> 2 guaranteed
    remainder = chance - guaranteed
    return float(guaranteed) + remainder


def expected_upgrades_per_wave(chance: float, waves_skipped: float = 0.0) -> float:
    """Expected upgrades gained per actual wave.

    Base: free upgrades trigger once after each wave.
    Additional triggers: when Wave Skip activates, free upgrades can trigger an additional
    time per workshop for each wave skipped.

    Parameters
    - chance: free upgrade chance as a fraction (1.0 == 100%)
    - waves_skipped: expected number of waves skipped associated with this actual wave

    Notes
    - We keep this deterministic by using expected triggers.
    - The distribution across individual stats within a category is handled elsewhere.
    """
    triggers = 1.0 + max(0.0, waves_skipped)
    return triggers * expected_upgrades_per_trigger(chance)
