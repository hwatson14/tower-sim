from pathlib import Path

import pytest

from v3.account_input_registry import load_all_account_input_registries, registry_counts
from v3.boundary_policy import (
    V3BoundaryPolicyError,
    assert_boundary_supported,
    assert_tick_precedence_supported,
)
from v3.kb_access import V3KBAccessError, read_csv_rows
from v3.mechanics_activation import build_domain_activation_plan, next_disabled_domain
from v3.milestones import evaluate_milestones

_IDS_FIXTURE = Path("tests/fixtures/tower-sim-data/_IDS.csv")


def test_step4_account_input_registry_loaders_cover_required_families() -> None:
    loaded = load_all_account_input_registries()
    assert set(loaded.keys()) == {"relic", "player_stuff", "theme_song", "unlock", "vault"}
    assert all(loaded[family] for family in loaded)
    counts = registry_counts()
    assert all(count > 0 for count in counts.values())


def test_step5_mechanics_activation_plan_order_and_gating() -> None:
    plan = build_domain_activation_plan()
    assert [row.domain for row in plan] == [
        "workshop",
        "labs",
        "cards",
        "modules",
        "ultimate-weapons",
        "bots",
        "perks",
        "combat",
        "enemies",
    ]
    assert plan[0].enabled is True
    assert all(not row.enabled for row in plan[1:])
    assert next_disabled_domain() == "labs"


def test_step6_closure_gate_rejects_noncanonical_mechanics_authority_path() -> None:
    with pytest.raises(V3KBAccessError, match="noncanonical_mechanics_surface"):
        read_csv_rows("kb/cards/notes/index.md", authority="mechanics")


def test_step6_boundary_checks_fail_closed() -> None:
    with pytest.raises(V3BoundaryPolicyError, match="accepted_unknown_boundary"):
        assert_boundary_supported(scope="tier_battle_condition_value", item_id="tanks_ultimate__lvl_20")
    with pytest.raises(V3BoundaryPolicyError, match="out_of_scope_tick_precedence"):
        assert_tick_precedence_supported(entity_id="BOT_FLAME_BOT")


def test_step7_milestone_status_evaluator() -> None:
    statuses = evaluate_milestones(_IDS_FIXTURE)
    by_name = {row.milestone: row for row in statuses}
    assert by_name["A"].status == "green"
    assert by_name["B"].status in {"in_progress", "green"}
    assert by_name["C"].status == "blocked"
