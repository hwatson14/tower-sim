
from __future__ import annotations

from tower_sim.run_context import RunContext, assert_perks_enabled

def apply_standard_perk_bonus_multiplicative(perk_base: float, quantity: int, standard_perk_bonus: float) -> float:
    """Compute multiplicative perk result per fandom formula.

    Inputs:
      perk_base: base as decimal (e.g., 0.20 for +20%)
      quantity: number of stacks (integer)
      standard_perk_bonus: decimal (e.g., 0.25 for +25% perk effectiveness)

    Returns:
      multiplier (e.g., 1.30 for +30%)
    """
    # Wiki: (1 + perk base × quantity) × (1 + standard perk bonus)
    return (1.0 + perk_base * quantity) * (1.0 + standard_perk_bonus)

def _apply_standard_perk_bonus_additive(
    perk_base: float,
    quantity: int,
    standard_perk_bonus: float,
) -> float:
    """Compute additive perk result per fandom formula.

    Wiki: Perk Base × quantity × (1 + standard perk bonus)
    Returns the additive amount (decimal), not 1+amount.
    """
    return perk_base * quantity * (1.0 + standard_perk_bonus)


def apply_standard_perk_bonus_multiplicative_checked(
    context: RunContext,
    perk_base: float,
    quantity: int,
    standard_perk_bonus: float,
) -> float:
    assert_perks_enabled(context)
    return apply_standard_perk_bonus_multiplicative(perk_base, quantity, standard_perk_bonus)


def apply_standard_perk_bonus_additive_checked(
    context: RunContext,
    perk_base: float,
    quantity: int,
    standard_perk_bonus: float,
) -> float:
    assert_perks_enabled(context)
    return apply_standard_perk_bonus_additive(perk_base, quantity, standard_perk_bonus)
