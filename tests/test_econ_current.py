import pytest

from tower_sim.engines.econ_current import (
    EPC_CARD_COINS,
    EPC_CARD_EOM,
    EPC_CARD_WS,
    EPC_CPK,
    EPC_FUP,
    EPC_GCOMP,
    EPC_SYNC,
    EPG_MODULE_BONUS,
    EconAdders,
    EconAssistLabs,
    EconBhInputs,
    EconCardCoins,
    EconCardEom,
    EconCardWSStack,
    EconCards,
    EconDwInputs,
    EconFupInputs,
    EconGbInputs,
    EconGCompInputs,
    EconGeneratorModule,
    EconGtInputs,
    EconInputs,
    EconLabs,
    EconMasteries,
    EconScalars,
    EconSpotlightInputs,
    EconToggles,
    EconUwInputs,
    EconWaveTimeInputs,
    EconWorkshop,
    GeneratorSubstats,
    StoneConstants,
    econ_current,
    spotlight_multiplier,
    wave_time_boost,
)


def test_econ_current_pipeline_outputs() -> None:
    inputs = EconInputs(
        labs=EconLabs(
            coins_per_kill_bonus_lvl=3,
            standard_perks_bonus_lvl=10,
            gt_bonus_lvl=5,
            gt_duration_lvl=4,
            bh_coin_bonus_lvl=6,
            dw_coin_bonus_lvl=2,
            spotlight_coin_bonus_lvl=1,
            gold_bot_cooldown_lvl=0,
            gold_bot_duration_lvl=0,
        ),
        masteries=EconMasteries(
            coins_mastery_lvl=0,
            extra_orb_mastery_lvl=0,
            wave_skip_mastery_lvl=0,
            intro_sprint_mastery_lvl=0,
            wave_accel_mastery_lvl=0,
        ),
        assist_labs=EconAssistLabs(
            assist_substats_generator_lvl=0,
            assist_substats_core_lvl=0,
            assist_bonus_generator_lvl=1.1,
        ),
        workshop=EconWorkshop(
            coins_per_kill_mult=1.5,
            free_attack_upgrade_rate=0.0,
        ),
        generator_substats=GeneratorSubstats(
            cpk_primary=0.05,
            cpk_assist=0.02,
            fup_primary=0.03,
            fup_assist=0.01,
            gcomp_primary=0.02,
            gcomp_assist=0.01,
        ),
        stone_constants=StoneConstants(
            gen_sac_scalar=0.2,
            gen_bonus_scalar=0.15,
            uw_scalar=0.0,
        ),
        scalars=EconScalars(
            base_scalar=1.2,
            time_multiplier_mode=1.2,
        ),
        adders=EconAdders(being_annihilator=0.5),
        toggles=EconToggles(has_coins_perk=True, has_econ=True),
        cards=EconCards(
            coins=EconCardCoins(
                enabled=True,
                level=5,
                mastery_enabled=True,
                mastery_level=2,
            ),
            eom=EconCardEom(has_card=True, level=4, is_enabled=True),
            ws_stack=EconCardWSStack(
                has_wsm=True,
                wsm_lvl=2,
                has_ism=True,
                ism_lvl=1,
                has_wam=True,
                wam_lvl=3,
                has_is=True,
                is_lvl=2,
                has_wacc=True,
                wacc_lvl=4,
                has_wam_mastery=True,
                has_intro=True,
                intro_mastery_lvl=1,
            ),
        ),
        generator_module=EconGeneratorModule(
            has_module=True,
            has_assist=True,
            primary_bonus=1.3,
        ),
        gcomp=EconGCompInputs(
            has_gcomp=True,
            gcomp_lvl=1,
            has_gcomp_mastery=True,
            gcomp_mastery_lvl=2,
            substat_type="",
            rarity="",
            prim_sub=0.02,
            ass_sub=0.01,
            e_econ=1.4,
        ),
        fup=EconFupInputs(
            has_att=True,
            att_lvl=4,
            has_att_mastery=True,
            has_gcomp=True,
            gcomp_lvl=2,
            has_gcomp_mastery=False,
            gcomp_mastery_lvl=0,
        ),
        uw=EconUwInputs(
            gt=EconGtInputs(
                owned=True,
                base_bonus=2.0,
                base_duration=30.0,
                base_cooldown=100.0,
                base_gcd=0.0,
                perk_active=False,
                perk_value=0.0,
                prim_sub=0.0,
                ass_sub=0.0,
                mvn_cd=0.0,
                ass_mvn_cd=0.0,
            ),
            bh=EconBhInputs(
                owned=True,
                base_duration=20.0,
                base_cooldown=80.0,
                perk_active=False,
                prim_sub=0.0,
                ass_sub=0.0,
                ass_mvn_cd=0.0,
            ),
            dw=EconDwInputs(
                owned=True,
                base_duration=10.0,
                base_cooldown=60.0,
            ),
            gb=EconGbInputs(
                owned=True,
                coin_multiplier=1.1,
                duration=15.0,
                cooldown=120.0,
                bonus_multiplier=1.05,
            ),
        ),
        spotlight=EconSpotlightInputs(has_spotlight=True, slcb=1.3, slq=2, sla=90),
        wave_time=EconWaveTimeInputs(
            has_wam=True,
            wam_lvl=2,
            has_is=True,
            is_lvl=5,
            has_is_mastery=True,
            has_wacc=True,
            standard_perks_bonus_lvl=10,
        ),
        econ_lvl=2,
        vault_pct=0.1,
    )

    outputs = econ_current(inputs)

    assert outputs.cpk == pytest.approx(4.542592384000001)
    assert outputs.free_upgrades_ws == pytest.approx(5.946234722420265)
    assert outputs.coins_card == pytest.approx(3.5)
    assert outputs.gen_bonus == pytest.approx(1.301495)
    assert outputs.eom == pytest.approx(1.12)
    assert outputs.avg_time_boost == pytest.approx(2.4067931999999996)
    assert outputs.sync == pytest.approx(1.8005)
    assert outputs.spotlight == pytest.approx(1.15)
    assert outputs.wave_time == pytest.approx(1.5321023076923077)
    assert outputs.base == pytest.approx(147.6514143587614)
    assert outputs.total == pytest.approx(524.6073450800967)


def test_econ_current_pure_functions() -> None:
    assert EPC_CPK(
        base=1.5,
        spb_lvl=10,
        stone_sac=0.2,
        rarity="",
        prim_sub=0.05,
        ass_sub=0.02,
        being_annihilator=0.5,
        has_coinsperk=True,
        coinsperk_lvl=3,
        has_econ=True,
        econ_lvl=2,
        vault_pct=0.1,
    ) == pytest.approx(4.542592384000001)
    assert EPC_CARD_COINS(True, 5, True, 2) == pytest.approx(3.5)
    assert EPC_CARD_EOM(True, 4, True) == pytest.approx(1.12)
    assert EPG_MODULE_BONUS(True, True, 1.3, 0.15, 1.1) == pytest.approx(1.301495)
    assert EPC_GCOMP(
        has_gcomp=True,
        gcomp_lvl=1,
        has_gcomp_mastery=True,
        gcomp_mastery_lvl=2,
        substat_type="",
        rarity="",
        prim_sub=0.02,
        ass_sub=0.01,
        stone_sac=0.2,
        has_econ=True,
        being_annihilator=0.5,
        eEcon=1.4,
    ) == pytest.approx(2.4067931999999996)
    assert EPC_FUP(
        has_att=True,
        att_lvl=4,
        has_att_mastery=True,
        has_gcomp=True,
        gcomp_lvl=2,
        has_gcomp_mastery=False,
        gcomp_mastery_lvl=0,
        prim_sub=0.03,
        ass_sub=0.01,
        stone_sac=0.2,
    ) == pytest.approx(1.7169390000000002)
    assert EPC_CARD_WS(
        has_wsm=True,
        wsm_lvl=2,
        has_ism=True,
        ism_lvl=1,
        has_wam=True,
        wam_lvl=3,
        has_is=True,
        is_lvl=2,
        has_wacc=True,
        wacc_lvl=4,
        has_wam_mastery=True,
        has_intro=True,
        intro_mastery_lvl=1,
    ) == pytest.approx(3.4632766349999997)
    assert EPC_SYNC(
        tmult=1.2,
        has_gt=True,
        has_bh=True,
        has_dw=True,
        has_gb=True,
        gtm=2.0,
        bhm=1.5,
        dwm=1.2,
        gbm=1.1,
        gtd=30.0,
        bhd=20.0,
        dwd=10.0,
        gbd=15.0,
        gtc=100.0,
        bhc=80.0,
        dwc=60.0,
        gbc=120.0,
        gtgc=0.0,
        gbb=1.05,
    ) == pytest.approx(1.5724999999999998)
    assert spotlight_multiplier(1.3, 2, 90) == pytest.approx(1.15)
    assert wave_time_boost(
        has_wam=True,
        wam_lvl=2,
        has_is=True,
        is_lvl=5,
        has_is_mastery=True,
        has_wacc=True,
        standard_perks_bonus=10,
    ) == pytest.approx(1.5321023076923077)
