"""Effective Paths econ (Current) deterministic formulas.

Provenance: Harry's Effective Paths eEcon (Current) reference sheet handoff
(`econ_current` spec in the user prompt). Constants and formulas below are
transcribed from that sheet (cells referenced in the handoff such as CG6, BA*,
BF*, BG5, BJ*).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EconLabs:
    coins_per_kill_bonus_lvl: int
    standard_perks_bonus_lvl: int
    gt_bonus_lvl: int
    gt_duration_lvl: int
    bh_coin_bonus_lvl: int
    dw_coin_bonus_lvl: int
    spotlight_coin_bonus_lvl: int
    gold_bot_cooldown_lvl: int
    gold_bot_duration_lvl: int


@dataclass(frozen=True)
class EconMasteries:
    coins_mastery_lvl: int
    extra_orb_mastery_lvl: int
    wave_skip_mastery_lvl: int
    intro_sprint_mastery_lvl: int
    wave_accel_mastery_lvl: int


@dataclass(frozen=True)
class EconAssistLabs:
    assist_substats_generator_lvl: int
    assist_substats_core_lvl: int
    assist_bonus_generator_lvl: float


@dataclass(frozen=True)
class EconWorkshop:
    coins_per_kill_mult: float
    free_attack_upgrade_rate: float


@dataclass(frozen=True)
class GeneratorSubstats:
    cpk_primary: float
    cpk_assist: float
    fup_primary: float
    fup_assist: float
    gcomp_primary: float
    gcomp_assist: float


@dataclass(frozen=True)
class StoneConstants:
    gen_sac_scalar: float
    gen_bonus_scalar: float
    uw_scalar: float


@dataclass(frozen=True)
class EconScalars:
    base_scalar: float
    time_multiplier_mode: float


@dataclass(frozen=True)
class EconAdders:
    being_annihilator: float


@dataclass(frozen=True)
class EconToggles:
    has_coins_perk: bool
    has_econ: bool


@dataclass(frozen=True)
class EconCardCoins:
    enabled: bool
    level: int
    mastery_enabled: bool
    mastery_level: int


@dataclass(frozen=True)
class EconCardEom:
    has_card: bool
    level: int
    is_enabled: bool


@dataclass(frozen=True)
class EconCardWSStack:
    has_wsm: bool
    wsm_lvl: int
    has_ism: bool
    ism_lvl: int
    has_wam: bool
    wam_lvl: int
    has_is: bool
    is_lvl: int
    has_wacc: bool
    wacc_lvl: int
    has_wam_mastery: bool
    has_intro: bool
    intro_mastery_lvl: int


@dataclass(frozen=True)
class EconCards:
    coins: EconCardCoins
    eom: EconCardEom
    ws_stack: EconCardWSStack


@dataclass(frozen=True)
class EconGeneratorModule:
    has_module: bool
    has_assist: bool
    primary_bonus: float


@dataclass(frozen=True)
class EconGCompInputs:
    has_gcomp: bool
    gcomp_lvl: int
    has_gcomp_mastery: bool
    gcomp_mastery_lvl: int
    substat_type: str
    rarity: str
    prim_sub: float
    ass_sub: float
    e_econ: float


@dataclass(frozen=True)
class EconFupInputs:
    has_att: bool
    att_lvl: int
    has_att_mastery: bool
    has_gcomp: bool
    gcomp_lvl: int
    has_gcomp_mastery: bool
    gcomp_mastery_lvl: int


@dataclass(frozen=True)
class EconGtInputs:
    owned: bool
    base_bonus: float
    base_duration: float
    base_cooldown: float
    base_gcd: float
    perk_active: bool
    perk_value: float
    prim_sub: float
    ass_sub: float
    mvn_cd: float
    ass_mvn_cd: float


@dataclass(frozen=True)
class EconBhInputs:
    owned: bool
    base_duration: float
    base_cooldown: float
    perk_active: bool
    prim_sub: float
    ass_sub: float
    ass_mvn_cd: float


@dataclass(frozen=True)
class EconDwInputs:
    owned: bool
    base_duration: float
    base_cooldown: float


@dataclass(frozen=True)
class EconGbInputs:
    owned: bool
    coin_multiplier: float
    duration: float
    cooldown: float
    bonus_multiplier: float


@dataclass(frozen=True)
class EconUwInputs:
    gt: EconGtInputs
    bh: EconBhInputs
    dw: EconDwInputs
    gb: EconGbInputs


@dataclass(frozen=True)
class EconSpotlightInputs:
    has_spotlight: bool
    slcb: float
    slq: float
    sla: float


@dataclass(frozen=True)
class EconWaveTimeInputs:
    has_wam: bool
    wam_lvl: int
    has_is: bool
    is_lvl: int
    has_is_mastery: bool
    has_wacc: bool
    standard_perks_bonus_lvl: int


@dataclass(frozen=True)
class EconInputs:
    labs: EconLabs
    masteries: EconMasteries
    assist_labs: EconAssistLabs
    workshop: EconWorkshop
    generator_substats: GeneratorSubstats
    stone_constants: StoneConstants
    scalars: EconScalars
    adders: EconAdders
    toggles: EconToggles
    cards: EconCards
    generator_module: EconGeneratorModule
    gcomp: EconGCompInputs
    fup: EconFupInputs
    uw: EconUwInputs
    spotlight: EconSpotlightInputs
    wave_time: EconWaveTimeInputs
    econ_lvl: int
    vault_pct: float


@dataclass(frozen=True)
class EconOutputs:
    base: float
    cpk: float
    free_upgrades_ws: float
    coins_card: float
    gen_bonus: float
    eom: float
    avg_time_boost: float
    sync: float
    spotlight: float
    wave_time: float
    total: float


def EPC_CPK(
    base: float,
    spb_lvl: int,
    stone_sac: float,
    rarity: str,
    prim_sub: float,
    ass_sub: float,
    being_annihilator: float,
    has_coinsperk: bool,
    coinsperk_lvl: int,
    has_econ: bool,
    econ_lvl: int,
    vault_pct: float,
) -> float:
    SPB = 1 + 0.01 * spb_lvl
    SAC = (1 + stone_sac) * 0.01
    Substat = 1 + prim_sub + ass_sub * SAC
    CoinsPerk = 1 + 0.10 * (1 + coinsperk_lvl) * SPB if has_coinsperk else 1
    Econ = 1 + 0.20 * (1 + econ_lvl) if has_econ else 1
    Vault = 1 + vault_pct
    _ = rarity
    return (base * Substat * CoinsPerk * Econ + being_annihilator) * Vault


def EPC_CARD_COINS(has_card: bool, card_level: int, has_mastery: bool, mastery_lvl: int) -> float:
    if not has_card:
        return 1
    mastery_mult = 1 + 0.25 * (1 + mastery_lvl) if has_mastery else 1
    return (1 + 0.2 * card_level) * mastery_mult


def EPC_CARD_EOM(has_card: bool, card_level: int, is_enabled: bool) -> float:
    return 1 + 0.03 * card_level if (has_card and is_enabled) else 1


def EPG_MODULE_BONUS(
    has_module: bool,
    has_assist: bool,
    prim_bonus: float,
    stone_bonus: float,
    lab_bonus: float,
) -> float:
    if not has_module:
        return 1
    assist_mult = (((lab_bonus - 1) * (1 + stone_bonus) * 0.01) + 1) if has_assist else 1
    return prim_bonus * assist_mult


def EPC_GCOMP(
    has_gcomp: bool,
    gcomp_lvl: int,
    has_gcomp_mastery: bool,
    gcomp_mastery_lvl: int,
    substat_type: str,
    rarity: str,
    prim_sub: float,
    ass_sub: float,
    stone_sac: float,
    has_econ: bool,
    being_annihilator: float,
    eEcon: float,
) -> float:
    SAC = (1 + stone_sac) * 0.01
    Substat = prim_sub + ass_sub * SAC
    GCOMP = 1 + (0.02 * (1 + gcomp_lvl)) + Substat if has_gcomp else 1
    GCOMPm = 1 + (0.05 * (1 + gcomp_mastery_lvl)) if has_gcomp_mastery else 1
    Econ = eEcon if has_econ else 1
    _ = (substat_type, rarity)
    return (GCOMP * GCOMPm + being_annihilator) * Econ


def EPC_SYNC(
    tmult: float,
    has_gt: bool,
    has_bh: bool,
    has_dw: bool,
    has_gb: bool,
    gtm: float,
    bhm: float,
    dwm: float,
    gbm: float,
    gtd: float,
    bhd: float,
    dwd: float,
    gbd: float,
    gtc: float,
    bhc: float,
    dwc: float,
    gbc: float,
    gtgc: float,
    gbb: float,
) -> float:
    GT = (gtm - 1) * (gtd / gtc) if has_gt else 0
    BH = (bhm - 1) * (bhd / bhc) if has_bh else 0
    DW = (dwm - 1) * (dwd / dwc) if has_dw else 0
    GB = (gbm - 1) * (gbd / gbc) if has_gb else 0
    GBB = (gbb - 1) * (gbd / gbc) if has_gb else 0
    _ = gtgc
    return 1 + tmult * (GT + BH + DW + GB + GBB)


def EPC_FUP(
    has_att: bool,
    att_lvl: int,
    has_att_mastery: bool,
    has_gcomp: bool,
    gcomp_lvl: int,
    has_gcomp_mastery: bool,
    gcomp_mastery_lvl: int,
    prim_sub: float,
    ass_sub: float,
    stone_sac: float,
) -> float:
    ATT = 1 + 0.01 * (1 + att_lvl) if has_att else 1
    ATTm = 1 + 0.10 * (1 + att_lvl) if has_att_mastery else 1
    SAC = (1 + stone_sac) * 0.01
    Substat = prim_sub + ass_sub * SAC
    GCOMP = 1 + (0.02 * (1 + gcomp_lvl)) + Substat if has_gcomp else 1
    GCOMPm = 1 + (0.05 * (1 + gcomp_mastery_lvl)) if has_gcomp_mastery else 1
    return ATT * ATTm * GCOMP * GCOMPm


def EPC_CARD_WS(
    has_wsm: bool,
    wsm_lvl: int,
    has_ism: bool,
    ism_lvl: int,
    has_wam: bool,
    wam_lvl: int,
    has_is: bool,
    is_lvl: int,
    has_wacc: bool,
    wacc_lvl: int,
    has_wam_mastery: bool,
    has_intro: bool,
    intro_mastery_lvl: int,
) -> float:
    WSM = 1 + 0.01 * (1 + wsm_lvl) if has_wsm else 1
    ISM = 1 + 0.01 * (1 + ism_lvl) if has_ism else 1
    WAM = 1 + 0.10 * (1 + wam_lvl) if has_wam else 1
    IS = 1 + 0.10 * (1 + is_lvl) if has_is else 1
    WACC = 1 + 0.01 * (1 + wacc_lvl) if has_wacc else 1
    WAMm = 1 + 0.03 * (1 + wacc_lvl) if has_wam_mastery else 1
    INTRO = 1 + 0.25 * (1 + intro_mastery_lvl) if has_intro else 1
    return WSM * ISM * WAM * IS * WACC * WAMm * INTRO


def EPC_GTB(
    gt_base_bonus: float,
    gt_bonus_lab: int,
    has_gt_perk: bool,
    perk_val: float,
    stone_sac: float,
    prim_sub: float,
    ass_sub: float,
) -> float:
    LAB = 1 + 0.05 * gt_bonus_lab
    PERK = 1 + perk_val if has_gt_perk else 1
    SAC = (1 + stone_sac) * 0.01
    Substat = 1 + prim_sub + ass_sub * SAC
    return gt_base_bonus * LAB * PERK * Substat


def EPC_GTD(gt_base_duration: float, gt_dur_lab: int, prim_sub: float, ass_sub: float) -> float:
    LAB = 1 + 0.05 * gt_dur_lab
    SAC = 0.01
    Substat = 1 + prim_sub + ass_sub * SAC
    return gt_base_duration * LAB * Substat


def EPC_GTCD(
    has_gt: bool,
    gt_cd: float,
    prim_sub: float,
    ass_sub: float,
    mvn_cd: float,
    ass_mvn_cd: float,
) -> float:
    SAC = (1 + mvn_cd + ass_mvn_cd) * 0.01
    Substat = prim_sub + ass_sub * SAC
    return gt_cd - Substat if has_gt else 0.0


def EPC_GTGC(has_gt: bool, gt_gcd: float, has_perk: bool, gtd: float) -> float:
    return gt_gcd + (0.2 * gtd if has_perk else 0) if has_gt else 0.0


def EPC_BHCB(has_perk: bool, lab_lvl: int) -> float:
    return 1 + 0.10 * lab_lvl if has_perk else 1 + 0.05 * lab_lvl


def EPC_BHD(bh_base_dur: float, has_perk: bool, prim_sub: float, ass_sub: float) -> float:
    PERK = 1.5 if has_perk else 1
    SAC = 0.01
    Substat = 1 + prim_sub + ass_sub * SAC
    return bh_base_dur * PERK * Substat


def EPC_BHCD(
    has_bh: bool,
    bh_cd: float,
    prim_sub: float,
    ass_sub: float,
    ass_mvn_cd: float,
) -> float:
    SAC = (1 + ass_mvn_cd) * 0.01
    Substat = prim_sub + ass_sub * SAC
    return bh_cd - Substat if has_bh else 0.0


def EPC_DWCB(lab_lvl: int) -> float:
    return 1 + 0.10 * lab_lvl


def spotlight_multiplier(slcb: float, slq: float, sla: float) -> float:
    return 1 + (slcb - 1) * min(1, (sla * slq) / 360)


def wave_time_boost(
    has_wam: bool,
    wam_lvl: int,
    has_is: bool,
    is_lvl: int,
    has_is_mastery: bool,
    has_wacc: bool,
    standard_perks_bonus: int,
) -> float:
    WAM = 6500 / (1 + 0.10 * (1 + wam_lvl)) if has_wam else 6500
    IS = (
        is_lvl
        - (1 + is_lvl / 10)
        + ((100 * 1.8 * (1 + standard_perks_bonus) - is_lvl) / 10 if has_is_mastery else 0)
        if has_is
        else 0
    )
    WACC = 1.5 * (1 + 0.01 * (1 + standard_perks_bonus)) if has_wacc else 1
    return 1 + (WAM + IS) * (WACC - 1) / 6500


def econ_current(inputs: EconInputs) -> EconOutputs:
    cpk = EPC_CPK(
        base=inputs.workshop.coins_per_kill_mult,
        spb_lvl=inputs.labs.standard_perks_bonus_lvl,
        stone_sac=inputs.stone_constants.gen_sac_scalar,
        rarity="",
        prim_sub=inputs.generator_substats.cpk_primary,
        ass_sub=inputs.generator_substats.cpk_assist,
        being_annihilator=inputs.adders.being_annihilator,
        has_coinsperk=inputs.toggles.has_coins_perk,
        coinsperk_lvl=inputs.labs.coins_per_kill_bonus_lvl,
        has_econ=inputs.toggles.has_econ,
        econ_lvl=inputs.econ_lvl,
        vault_pct=inputs.vault_pct,
    )

    free_upgrades_ws = EPC_FUP(
        has_att=inputs.fup.has_att,
        att_lvl=inputs.fup.att_lvl,
        has_att_mastery=inputs.fup.has_att_mastery,
        has_gcomp=inputs.fup.has_gcomp,
        gcomp_lvl=inputs.fup.gcomp_lvl,
        has_gcomp_mastery=inputs.fup.has_gcomp_mastery,
        gcomp_mastery_lvl=inputs.fup.gcomp_mastery_lvl,
        prim_sub=inputs.generator_substats.fup_primary,
        ass_sub=inputs.generator_substats.fup_assist,
        stone_sac=inputs.stone_constants.gen_sac_scalar,
    ) * EPC_CARD_WS(
        has_wsm=inputs.cards.ws_stack.has_wsm,
        wsm_lvl=inputs.cards.ws_stack.wsm_lvl,
        has_ism=inputs.cards.ws_stack.has_ism,
        ism_lvl=inputs.cards.ws_stack.ism_lvl,
        has_wam=inputs.cards.ws_stack.has_wam,
        wam_lvl=inputs.cards.ws_stack.wam_lvl,
        has_is=inputs.cards.ws_stack.has_is,
        is_lvl=inputs.cards.ws_stack.is_lvl,
        has_wacc=inputs.cards.ws_stack.has_wacc,
        wacc_lvl=inputs.cards.ws_stack.wacc_lvl,
        has_wam_mastery=inputs.cards.ws_stack.has_wam_mastery,
        has_intro=inputs.cards.ws_stack.has_intro,
        intro_mastery_lvl=inputs.cards.ws_stack.intro_mastery_lvl,
    )

    coins_card = EPC_CARD_COINS(
        has_card=inputs.cards.coins.enabled,
        card_level=inputs.cards.coins.level,
        has_mastery=inputs.cards.coins.mastery_enabled,
        mastery_lvl=inputs.cards.coins.mastery_level,
    )

    gen_bonus = EPG_MODULE_BONUS(
        has_module=inputs.generator_module.has_module,
        has_assist=inputs.generator_module.has_assist,
        prim_bonus=inputs.generator_module.primary_bonus,
        stone_bonus=inputs.stone_constants.gen_bonus_scalar,
        lab_bonus=inputs.assist_labs.assist_bonus_generator_lvl,
    )

    base = inputs.scalars.base_scalar * cpk * free_upgrades_ws * coins_card * gen_bonus

    eom = EPC_CARD_EOM(
        has_card=inputs.cards.eom.has_card,
        card_level=inputs.cards.eom.level,
        is_enabled=inputs.cards.eom.is_enabled,
    )

    avg_time_boost = EPC_GCOMP(
        has_gcomp=inputs.gcomp.has_gcomp,
        gcomp_lvl=inputs.gcomp.gcomp_lvl,
        has_gcomp_mastery=inputs.gcomp.has_gcomp_mastery,
        gcomp_mastery_lvl=inputs.gcomp.gcomp_mastery_lvl,
        substat_type=inputs.gcomp.substat_type,
        rarity=inputs.gcomp.rarity,
        prim_sub=inputs.gcomp.prim_sub,
        ass_sub=inputs.gcomp.ass_sub,
        stone_sac=inputs.stone_constants.gen_sac_scalar,
        has_econ=inputs.toggles.has_econ,
        being_annihilator=inputs.adders.being_annihilator,
        eEcon=inputs.gcomp.e_econ,
    )

    gtm = EPC_GTB(
        gt_base_bonus=inputs.uw.gt.base_bonus,
        gt_bonus_lab=inputs.labs.gt_bonus_lvl,
        has_gt_perk=inputs.uw.gt.perk_active,
        perk_val=inputs.uw.gt.perk_value,
        stone_sac=inputs.stone_constants.uw_scalar,
        prim_sub=inputs.uw.gt.prim_sub,
        ass_sub=inputs.uw.gt.ass_sub,
    )
    gtd = EPC_GTD(
        gt_base_duration=inputs.uw.gt.base_duration,
        gt_dur_lab=inputs.labs.gt_duration_lvl,
        prim_sub=inputs.uw.gt.prim_sub,
        ass_sub=inputs.uw.gt.ass_sub,
    )
    gtc = EPC_GTCD(
        has_gt=inputs.uw.gt.owned,
        gt_cd=inputs.uw.gt.base_cooldown,
        prim_sub=inputs.uw.gt.prim_sub,
        ass_sub=inputs.uw.gt.ass_sub,
        mvn_cd=inputs.uw.gt.mvn_cd,
        ass_mvn_cd=inputs.uw.gt.ass_mvn_cd,
    )
    gtgc = EPC_GTGC(
        has_gt=inputs.uw.gt.owned,
        gt_gcd=inputs.uw.gt.base_gcd,
        has_perk=inputs.uw.gt.perk_active,
        gtd=gtd,
    )

    bhm = EPC_BHCB(inputs.uw.bh.perk_active, inputs.labs.bh_coin_bonus_lvl)
    bhd = EPC_BHD(
        bh_base_dur=inputs.uw.bh.base_duration,
        has_perk=inputs.uw.bh.perk_active,
        prim_sub=inputs.uw.bh.prim_sub,
        ass_sub=inputs.uw.bh.ass_sub,
    )
    bhc = EPC_BHCD(
        has_bh=inputs.uw.bh.owned,
        bh_cd=inputs.uw.bh.base_cooldown,
        prim_sub=inputs.uw.bh.prim_sub,
        ass_sub=inputs.uw.bh.ass_sub,
        ass_mvn_cd=inputs.uw.bh.ass_mvn_cd,
    )

    dwm = EPC_DWCB(inputs.labs.dw_coin_bonus_lvl)

    sync = EPC_SYNC(
        tmult=inputs.scalars.time_multiplier_mode,
        has_gt=inputs.uw.gt.owned,
        has_bh=inputs.uw.bh.owned,
        has_dw=inputs.uw.dw.owned,
        has_gb=inputs.uw.gb.owned,
        gtm=gtm,
        bhm=bhm,
        dwm=dwm,
        gbm=inputs.uw.gb.coin_multiplier,
        gtd=gtd,
        bhd=bhd,
        dwd=inputs.uw.dw.base_duration,
        gbd=inputs.uw.gb.duration,
        gtc=gtc,
        bhc=bhc,
        dwc=inputs.uw.dw.base_cooldown,
        gbc=inputs.uw.gb.cooldown,
        gtgc=gtgc,
        gbb=inputs.uw.gb.bonus_multiplier,
    )

    spotlight = (
        spotlight_multiplier(inputs.spotlight.slcb, inputs.spotlight.slq, inputs.spotlight.sla)
        if inputs.spotlight.has_spotlight
        else 1
    )

    wave_time = wave_time_boost(
        has_wam=inputs.wave_time.has_wam,
        wam_lvl=inputs.wave_time.wam_lvl,
        has_is=inputs.wave_time.has_is,
        is_lvl=inputs.wave_time.is_lvl,
        has_is_mastery=inputs.wave_time.has_is_mastery,
        has_wacc=inputs.wave_time.has_wacc,
        standard_perks_bonus=inputs.wave_time.standard_perks_bonus_lvl,
    )

    total = base * eom * sync * spotlight * wave_time

    return EconOutputs(
        base=base,
        cpk=cpk,
        free_upgrades_ws=free_upgrades_ws,
        coins_card=coins_card,
        gen_bonus=gen_bonus,
        eom=eom,
        avg_time_boost=avg_time_boost,
        sync=sync,
        spotlight=spotlight,
        wave_time=wave_time,
        total=total,
    )


__all__ = [
    "EPC_BHCB",
    "EPC_BHCD",
    "EPC_BHD",
    "EPC_CARD_COINS",
    "EPC_CARD_EOM",
    "EPC_CARD_WS",
    "EPC_CPK",
    "EPC_DWCB",
    "EPC_FUP",
    "EPC_GCOMP",
    "EPC_GTB",
    "EPC_GTCD",
    "EPC_GTD",
    "EPC_GTGC",
    "EPC_SYNC",
    "EPG_MODULE_BONUS",
    "EconAdders",
    "EconAssistLabs",
    "EconBhInputs",
    "EconCardCoins",
    "EconCardEom",
    "EconCardWSStack",
    "EconCards",
    "EconDwInputs",
    "EconFupInputs",
    "EconGbInputs",
    "EconGCompInputs",
    "EconGeneratorModule",
    "EconInputs",
    "EconLabs",
    "EconMasteries",
    "EconOutputs",
    "EconScalars",
    "EconSpotlightInputs",
    "EconToggles",
    "EconUwInputs",
    "EconWaveTimeInputs",
    "EconWorkshop",
    "GeneratorSubstats",
    "StoneConstants",
    "econ_current",
    "spotlight_multiplier",
    "wave_time_boost",
]
