from __future__ import annotations

_PRESET_TO_DAYS = {
    "immediate": 0,
    "week": 7,
    "month": 30,
}

def build_module_planner_horizon_profile(horizon_kind: str, custom_days: int | None = None) -> dict:
    if horizon_kind not in {"immediate", "week", "month", "custom"}:
        raise ValueError(f"unsupported horizon_kind: {horizon_kind}")

    if horizon_kind == "custom":
        if custom_days is None or custom_days <= 0:
            raise ValueError("custom horizon requires positive custom_days")
        horizon_days = int(custom_days)
    else:
        if custom_days is not None:
            raise ValueError("custom_days may only be provided for custom horizon")
        horizon_days = _PRESET_TO_DAYS[horizon_kind]

    return {
        "horizon_kind": horizon_kind,
        "horizon_days": horizon_days,
        "is_immediate": horizon_kind == "immediate",
        "is_time_based": horizon_days > 0,
    }
