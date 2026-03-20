from compilers.stat_input_compiler import compiler_routing_policy


def test_compiler_routing_policy_contract_extracts_scope_and_overrides():
    policy = compiler_routing_policy()
    assert "Unlock Perks" in policy["non_calculator_scope_labs"]
    assert policy["uw_mechanic_destination_overrides"][("Golden Tower", "Multiplier")] == ("mechanic_param", "uw.golden_tower.bonus_multiplier")
    assert policy["uw_contributor_overrides"][("Death Wave", "Quantity")] == "uw_upgrade__death_wave__effect_wave_count__count"
    assert policy["guardian_destination_overrides"][("Scout", "Duration")] == ("mechanic_param", "guardian.scout.duration_seconds")
    assert policy["vault_boolean_flags"]["bot presets"] == ("account_flag", "account_flag.bot_presets")
    assert policy["relic_alias_overrides"]["bot range"] == ("mechanic_param", "bot.global.range_bonus_m")
