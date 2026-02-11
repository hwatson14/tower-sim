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
    return evaluate_lambda(
        "EPD_ASPD",
        {
            "ws_level": ws_level,
            "wsp_level": wsp_level,
            "lab_level": lab_level,
            "has_card": has_card,
            "card_level": card_level,
            "substat": substat,
            "relic": relic,
            "vault": vault,
            "has_mastery": has_mastery,
            "mastery_level": mastery_level,
        },
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
    """EPD_CRIT_CHANCE from Effective Paths mechanics registry."""
    return evaluate_lambda(
        "EPD_CRIT_CHANCE",
        {
            "ws_level": ws_level,
            "has_card": has_card,
            "card_level": card_level,
            "relic": relic,
            "vault": vault,
            "substat": substat,
            "has_mastery": has_mastery,
            "mastery_level": mastery_level,
        },
    )


def epd_critical(
    crit_chance: float,
    crit_factor: float,
    super_crit_chance: float,
    super_crit_mult: float,
    being_annihilator: float,
) -> float:
    """EPD_CRITICAL from Effective Paths mechanics registry."""
    return evaluate_lambda(
        "EPD_CRITICAL",
        {
            "cc": crit_chance,
            "cf": crit_factor,
            "scc": super_crit_chance,
            "scm": super_crit_mult,
            "being_annihilator": being_annihilator,
        },
    )


__all__ = [
    "bullet_per_second",
    "epd_aspd",
    "epd_crit_chance",
    "epd_critical",
]
