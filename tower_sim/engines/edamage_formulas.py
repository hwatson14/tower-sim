from __future__ import annotations

from tower_sim.evaluators.ep_formula_evaluator import evaluate_lambda


def bullet_per_second(attack_speed: float) -> float:
    """BULLET_PER_SECOND from Effective Paths mechanics registry."""
    return evaluate_lambda("BULLET_PER_SECOND", {"attack_speed": attack_speed})


def epd_aspd(
    ws_level: float,
    wsp_level: float,
    lab_level: float,
    has_card: bool,
    card_level: float,
    substat: float,
    relic: float,
    vault: float,
    has_mastery: bool,
    mastery_level: float,
) -> float:
    """EPD_ASPD from Effective Paths eDamage extract (DJ5 -> EPD_ASPD)."""
    ws = 1 / (1 + ws_level * 0.02)
    ws_plus = 1 / (1 + wsp_level * 0.01)
    lab = 1 / (1 + lab_level * 0.02)
    card_aspd = 1 / (1 + card_level * 0.02) if has_card else 1
    substat_value = 1 / (1 + substat)
    mastery = 1 / (1 + (0.005 * (1 + mastery_level))) if has_mastery else 1
    relic_bonus = 1 / (1 + relic)
    vault_bonus = 1 / (1 + vault)
    return (
        ws
        * ws_plus
        * lab
        * card_aspd
        * substat_value
        * mastery
        * relic_bonus
        * vault_bonus
    )


def epd_crit_chance(
    ws_level: float,
    has_card: bool,
    card_level: float,
    relic: float,
    vault: float,
    substat: float,
    has_mastery: bool,
    mastery_level: float,
) -> float:
    """EPD_CRIT_CHANCE from Effective Paths eDamage extract (CZ5 -> EPD_CRIT_CHANCE)."""
    ws = ws_level * 0.003
    card_cc = card_level * 0.0015 if has_card else 0.0
    mastery = 0.001 * (1 + mastery_level) if has_mastery else 0.0
    return ws + card_cc + substat + relic + vault + mastery


def epd_critical(
    crit_chance: float,
    crit_factor: float,
    super_crit_chance: float,
    super_crit_mult: float,
    being_annihilator: float,
) -> float:
    """EPD_CRITICAL from Effective Paths eDamage extract (DD5 -> EPD_CRITICAL)."""
    cc = min(1.0, crit_chance)
    normal_crit = 1 + cc * (crit_factor - 1)
    super_crit_chance = min(cc, super_crit_chance)
    super_crit = 1 + super_crit_chance * (super_crit_mult - crit_factor)
    return normal_crit * super_crit + being_annihilator


__all__ = [
    "bullet_per_second",
    "epd_aspd",
    "epd_crit_chance",
    "epd_critical",
]
