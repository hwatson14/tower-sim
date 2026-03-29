from __future__ import annotations

from input.state_types import AccountState
from simulators.perk_timeline_state import apply_perk_counts_to_account_state


def apply_checkpoint_perk_state(
    account_state: AccountState,
    *,
    perk_counts_override: dict[str, int] | None,
) -> AccountState:
    if not perk_counts_override:
        return account_state
    return apply_perk_counts_to_account_state(
        account_state,
        perk_counts=perk_counts_override,
    )
