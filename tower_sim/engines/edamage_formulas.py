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
    """EPD_ASPD from Effective Paths mechanics registry."""
    ws = 1 + 0.05 * ws_level
    ws_plus = 1 + 0.01 * wsp_level
    lab = 1 + 0.02 * lab_level
    card_aspd = (
        (1.1 + card_level * 0.15)
        * (1 + 0.03 * (1 + mastery_level) if has_mastery else 1)
        if has_card
        else 1
    )
    relic_bonus = 1 + relic
    vault_bonus = 1 + vault
    return (ws * lab * card_aspd + substat) * ws_plus * relic_bonus * vault_bonus


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
    """EPD_CRIT_CHANCE from Effective Paths mechanics registry."""
    ws = 0.01 + (0.01 * ws_level)
    card_cc = (
        0.04
        + 0.01 * card_level
        + (0.01 * (1 + mastery_level) if has_mastery else 0)
        if has_card
        else 0
    )
    return ws + relic + vault + substat + card_cc


def epd_critical(
    crit_chance: float,
    crit_factor: float,
    super_crit_chance: float,
    super_crit_mult: float,
    being_annihilator: float,
) -> float:
    """EPD_CRITICAL from Effective Paths mechanics registry."""
    cc = min(1.0, crit_chance)
    normal_crit = (1 - cc) + (cc * crit_factor * (1 - super_crit_chance)) + (
        cc * crit_factor * super_crit_chance * super_crit_mult
    )
    streak = being_annihilator
    streak_chance = cc * super_crit_chance
    denom = 1 + (streak * streak_chance)
    pi_zero = 1 / denom
    pi_streak = (streak * streak_chance) / denom
    ba_crit_factor = crit_factor * super_crit_mult
    return (pi_zero * normal_crit) + (pi_streak * ba_crit_factor)


__all__ = [
    "bullet_per_second",
    "epd_aspd",
    "epd_crit_chance",
    "epd_critical",
]
