"""
input/run_tracker.py -- Tower Run Tracker export parsing.

Owns: parsing external Tower Run Tracker CSV exports into bounded observation
summaries. Does not own mechanic truth, calibration formulas, or account state.
"""
from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Iterable


_NUMBER_MULTIPLIERS = {
    "": 1.0,
    "K": 1_000.0,
    "M": 1_000_000.0,
    "B": 1_000_000_000.0,
    "T": 1_000_000_000_000.0,
    "q": 1_000_000_000_000_000.0,
}
_NUMBER_RE = re.compile(r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*([A-Za-z]*)\s*$")
_DURATION_RE = re.compile(r"(?:(?P<days>\d+)d)?(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+(?:\.\d+)?)s)?$")
_REQUIRED_COLUMNS = (
    "createdAt",
    "tier",
    "wave",
    "duration",
    "coins",
    "type",
    "runDate",
    "coinsPerHour",
)
_NORMAL_ENEMY_FIELDS = (
    ("basic", "Basic"),
    ("fast", "Fast"),
    ("tank", "Tank"),
    ("ranged", "Ranged"),
    ("boss", "Boss"),
    ("protector", "Protector"),
)
_ELITE_ENEMY_FIELDS = (
    ("vampires", "Vampires"),
    ("rays", "Rays"),
    ("scatters", "Scatters"),
    ("saboteurs", "Saboteurs"),
    ("commanders", "Commanders"),
    ("overcharges", "Overcharges"),
)


@dataclass(frozen=True)
class RunTrackerRecord:
    source_row: int
    run_type: str
    tier_raw: str
    tier: int | None
    wave: int | None
    duration_seconds: float | None
    game_time_seconds: float | None
    coins: float | None
    coins_per_hour: float | None
    cells: float | None
    cells_per_hour: float | None
    waves_skipped: int | None
    coins_from_wave_skip: float | None
    coins_per_wave: float | None
    most_coins_from_wave_skip: float | None
    coins_from_death_wave: float | None
    coins_from_golden_tower: float | None
    coins_from_black_hole: float | None
    coins_from_spotlight: float | None
    golden_bot_coins_earned: float | None
    coins_from_golden_combo: float | None
    total_enemies: int | None
    basic: int | None
    fast: int | None
    tank: int | None
    ranged: int | None
    boss: int | None
    protector: int | None
    total_elites: int | None
    vampires: int | None
    rays: int | None
    scatters: int | None
    saboteurs: int | None
    commanders: int | None
    overcharges: int | None
    enemies_per_hour: float | None
    waves_per_hour: float | None
    killed_by: str
    note: str
    verified: bool | None
    run_date: str
    run_time: str
    created_at: str
    updated_at: str


def parse_tracker_number(value: object) -> float | None:
    """Parse Tower Run Tracker compact numbers such as 240.70T or 1.63q."""
    raw = "" if value is None else str(value).strip()
    if not raw:
        return None
    match = _NUMBER_RE.match(raw.replace(",", ""))
    if not match:
        return None
    suffix = match.group(2)
    multiplier = _NUMBER_MULTIPLIERS.get(suffix)
    if multiplier is None:
        return None
    return float(match.group(1)) * multiplier


def parse_tracker_int(value: object) -> int | None:
    parsed = parse_tracker_number(value)
    return None if parsed is None else int(round(parsed))


def parse_tracker_duration_seconds(value: object) -> float | None:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return None
    match = _DURATION_RE.fullmatch(raw)
    if not match:
        return None
    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = float(match.group("seconds") or 0.0)
    return days * 86400.0 + hours * 3600.0 + minutes * 60.0 + seconds


def _parse_bool(value: object) -> bool | None:
    raw = "" if value is None else str(value).strip().lower()
    if raw in {"true", "1", "yes"}:
        return True
    if raw in {"false", "0", "no"}:
        return False
    return None


def _parse_tier(value: object) -> int | None:
    raw = "" if value is None else str(value).strip()
    return int(raw) if raw.isdigit() else None


def _record_sort_key(record: RunTrackerRecord) -> tuple[str, str, int]:
    return (record.run_date, record.run_time, record.source_row)


def parse_run_tracker_csv(path: Path) -> list[RunTrackerRecord]:
    if not path.exists():
        raise FileNotFoundError(f"Tower Run Tracker CSV not found: {path}")

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        records: list[RunTrackerRecord] = []
        for index, row in enumerate(reader, start=2):
            records.append(
                RunTrackerRecord(
                    source_row=index,
                    run_type=str(row.get("type") or "").strip() or "Unknown",
                    tier_raw=str(row.get("tier") or "").strip(),
                    tier=_parse_tier(row.get("tier")),
                    wave=parse_tracker_int(row.get("wave")),
                    duration_seconds=parse_tracker_duration_seconds(row.get("duration")),
                    game_time_seconds=parse_tracker_duration_seconds(row.get("gameTime")),
                    coins=parse_tracker_number(row.get("coins")),
                    coins_per_hour=parse_tracker_number(row.get("coinsPerHour")),
                    cells=parse_tracker_number(row.get("cells")),
                    cells_per_hour=parse_tracker_number(row.get("cellsPerHour")),
                    waves_skipped=parse_tracker_int(row.get("wavesSkipped")),
                    coins_from_wave_skip=parse_tracker_number(row.get("coinsFromWaveSkip")),
                    coins_per_wave=parse_tracker_number(row.get("coinsPerWave")),
                    most_coins_from_wave_skip=parse_tracker_number(
                        row.get("mostCoinsFromWaveSkip")
                    ),
                    coins_from_death_wave=parse_tracker_number(row.get("coinsFromDeathWave")),
                    coins_from_golden_tower=parse_tracker_number(row.get("coinsFromGoldenTower")),
                    coins_from_black_hole=parse_tracker_number(row.get("coinsFromBlackhole")),
                    coins_from_spotlight=parse_tracker_number(row.get("coinsFromSpotlight")),
                    golden_bot_coins_earned=parse_tracker_number(row.get("goldenBotCoinsEarned")),
                    coins_from_golden_combo=parse_tracker_number(row.get("coinsFromGoldenCombo")),
                    total_enemies=parse_tracker_int(row.get("totalEnemies")),
                    basic=parse_tracker_int(row.get("basic")),
                    fast=parse_tracker_int(row.get("fast")),
                    tank=parse_tracker_int(row.get("tank")),
                    ranged=parse_tracker_int(row.get("ranged")),
                    boss=parse_tracker_int(row.get("boss")),
                    protector=parse_tracker_int(row.get("protector")),
                    total_elites=parse_tracker_int(row.get("totalElites")),
                    vampires=parse_tracker_int(row.get("vampires")),
                    rays=parse_tracker_int(row.get("rays")),
                    scatters=parse_tracker_int(row.get("scatters")),
                    saboteurs=parse_tracker_int(row.get("saboteurs")),
                    commanders=parse_tracker_int(row.get("commanders")),
                    overcharges=parse_tracker_int(row.get("overcharges")),
                    enemies_per_hour=parse_tracker_number(row.get("enemiesPerHour")),
                    waves_per_hour=parse_tracker_number(row.get("wavesPerHour")),
                    killed_by=str(row.get("killedBy") or "").strip(),
                    note=str(row.get("note") or "").strip(),
                    verified=_parse_bool(row.get("verified")),
                    run_date=str(row.get("runDate") or row.get("date") or "").strip(),
                    run_time=str(row.get("runTime") or row.get("time") or "").strip(),
                    created_at=str(row.get("createdAt") or "").strip(),
                    updated_at=str(row.get("updatedAt") or "").strip(),
                )
            )
    return records


def _compact_stats(values: Iterable[float | int | None]) -> dict[str, object]:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return {"count": 0}
    return {
        "count": len(clean),
        "min": min(clean),
        "max": max(clean),
        "mean": mean(clean),
        "median": median(clean),
    }


def _record_date_range(records: list[RunTrackerRecord]) -> dict[str, object]:
    ordered = sorted(records, key=_record_sort_key)
    return {
        "min_run_date": ordered[0].run_date if ordered else None,
        "max_run_date": ordered[-1].run_date if ordered else None,
    }


def _tracker_count_share(record: RunTrackerRecord, value: int | None) -> float | None:
    if value is None or record.total_enemies in (None, 0):
        return None
    return float(value) / float(record.total_enemies)


def _tracker_count_per_wave(record: RunTrackerRecord, value: int | None) -> float | None:
    if value is None or record.wave in (None, 0):
        return None
    return float(value) / float(record.wave)


def _tracker_field_sum(record: RunTrackerRecord, fields: Iterable[str]) -> float | None:
    values = [getattr(record, field) for field in fields]
    if not any(value is not None for value in values):
        return None
    return sum(float(value or 0) for value in values)


def _tracker_field_sum_share(record: RunTrackerRecord, fields: Iterable[str]) -> float | None:
    total = _tracker_field_sum(record, fields)
    if total is None or record.total_enemies in (None, 0):
        return None
    return float(total) / float(record.total_enemies)


def _tracker_field_sum_per_wave(record: RunTrackerRecord, fields: Iterable[str]) -> float | None:
    total = _tracker_field_sum(record, fields)
    if total is None or record.wave in (None, 0):
        return None
    return float(total) / float(record.wave)


def _tracker_enemy_composition_summary(records: list[RunTrackerRecord]) -> dict[str, object]:
    def _group(fields: tuple[tuple[str, str], ...]) -> dict[str, dict[str, object]]:
        return {
            field_name: {
                "label": label,
                "count": _compact_stats(getattr(record, field_name) for record in records),
                "count_per_wave": _compact_stats(
                    _tracker_count_per_wave(record, getattr(record, field_name))
                    for record in records
                ),
                "share_of_total_enemies": _compact_stats(
                    _tracker_count_share(record, getattr(record, field_name))
                    for record in records
                ),
            }
            for field_name, label in fields
        }

    normal = _group(_NORMAL_ENEMY_FIELDS)
    elites = _group(_ELITE_ENEMY_FIELDS)
    normal_count = sum(
        1
        for field_name, _label in _NORMAL_ENEMY_FIELDS
        if int((normal[field_name]["count"] or {}).get("count") or 0) > 0
    )
    elite_count = sum(
        1
        for field_name, _label in _ELITE_ENEMY_FIELDS
        if int((elites[field_name]["count"] or {}).get("count") or 0) > 0
    )
    normal_fields = tuple(field for field, _label in _NORMAL_ENEMY_FIELDS)
    elite_fields = tuple(field for field, _label in _ELITE_ENEMY_FIELDS)
    return {
        "status": (
            "tracker_enemy_composition_available"
            if normal_count or elite_count
            else "not_supplied"
        ),
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
        "available_normal_enemy_field_count": normal_count,
        "available_elite_enemy_field_count": elite_count,
        "normal_enemy_counts": normal,
        "elite_enemy_counts": elites,
        "normal_tracked_share_of_total_enemies": _compact_stats(
            _tracker_field_sum_share(record, normal_fields) for record in records
        ),
        "normal_tracked_count_per_wave": _compact_stats(
            _tracker_field_sum_per_wave(record, normal_fields) for record in records
        ),
        "elite_tracked_share_of_total_enemies": _compact_stats(
            _tracker_field_sum_share(record, elite_fields) for record in records
        ),
        "elite_tracked_count_per_wave": _compact_stats(
            _tracker_field_sum_per_wave(record, elite_fields) for record in records
        ),
        "total_elites_share_of_total_enemies": _compact_stats(
            _tracker_count_share(record, record.total_elites) for record in records
        ),
        "total_elites_per_wave": _compact_stats(
            _tracker_count_per_wave(record, record.total_elites) for record in records
        ),
        "interpretation": (
            "Tracker enemy composition is external pressure-shape evidence only; "
            "it does not define spawn tables, elite pressure weights, or terminal max-wave formulas."
        ),
    }


def _trend_metric(
    *,
    recent: dict[str, object],
    prior: dict[str, object],
) -> dict[str, object]:
    recent_median = recent.get("median")
    prior_median = prior.get("median")
    delta = None
    ratio = None
    direction = "not_available"
    try:
        if recent_median is not None and prior_median is not None:
            delta = float(recent_median) - float(prior_median)
            if float(prior_median) != 0.0:
                ratio = float(recent_median) / float(prior_median)
            if delta > 0.0:
                direction = "up"
            elif delta < 0.0:
                direction = "down"
            else:
                direction = "flat"
    except (TypeError, ValueError):
        delta = None
        ratio = None
        direction = "not_available"
    return {
        "recent": recent,
        "prior": prior,
        "median_delta": delta,
        "median_ratio": ratio,
        "direction": direction,
    }


_ECON_COIN_SOURCE_FIELDS = (
    ("coins_from_death_wave", "Death Wave"),
    ("coins_from_golden_tower", "Golden Tower"),
    ("coins_from_black_hole", "Black Hole"),
    ("coins_from_spotlight", "Spotlight"),
    ("golden_bot_coins_earned", "Golden Bot"),
    ("coins_from_golden_combo", "Golden Combo"),
)


def _tracker_coin_share(record: RunTrackerRecord, value: float | None) -> float | None:
    if value is None or record.coins in (None, 0):
        return None
    return float(value) / float(record.coins)


def _tracker_econ_coin_source_sum(record: RunTrackerRecord) -> float | None:
    values = [
        getattr(record, field_name)
        for field_name, _label in _ECON_COIN_SOURCE_FIELDS
        if getattr(record, field_name) is not None
    ]
    if not values:
        return None
    return sum(float(value) for value in values)


def _tracker_econ_coin_source_sum_ratio(record: RunTrackerRecord) -> float | None:
    source_sum = _tracker_econ_coin_source_sum(record)
    if source_sum is None or record.coins in (None, 0):
        return None
    return float(source_sum) / float(record.coins)


def _tracker_econ_coin_source_summary(records: list[RunTrackerRecord]) -> dict[str, object]:
    sources: dict[str, dict[str, object]] = {}
    available = 0
    for field_name, label in _ECON_COIN_SOURCE_FIELDS:
        values = [getattr(record, field_name) for record in records]
        coins = _compact_stats(values)
        shares = _compact_stats(
            _tracker_coin_share(record, getattr(record, field_name)) for record in records
        )
        if int(coins.get("count") or 0) > 0:
            available += 1
        sources[field_name] = {
            "label": label,
            "coins": coins,
            "share_of_run_coins": shares,
        }
    source_sum = _compact_stats(_tracker_econ_coin_source_sum(record) for record in records)
    source_sum_ratio = _compact_stats(
        _tracker_econ_coin_source_sum_ratio(record) for record in records
    )
    median_sum_ratio = source_sum_ratio.get("median")
    overlap_status = "not_available"
    try:
        if median_sum_ratio is not None:
            overlap_status = (
                "source_splits_overlap_or_double_count"
                if float(median_sum_ratio) > 1.0
                else "source_splits_do_not_exceed_total"
            )
    except (TypeError, ValueError):
        overlap_status = "not_available"
    return {
        "status": (
            "tracker_econ_coin_sources_available" if available else "not_supplied"
        ),
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
        "available_source_count": available,
        "tracked_source_count": len(_ECON_COIN_SOURCE_FIELDS),
        "tracked_source_coin_sum": source_sum,
        "tracked_source_sum_to_run_coins_ratio": source_sum_ratio,
        "overlap_evidence_status": overlap_status,
        "sources": sources,
        "interpretation": (
            "Tracker econ source coin splits are calibration evidence only. "
            "They do not define overlap math, kill attribution, or certified CPH."
        ),
    }


def _farming_t14_recent_trend(
    records: list[RunTrackerRecord],
    *,
    recent_window: int,
) -> dict[str, object]:
    if recent_window <= 0:
        recent_window = 10
    recent = records[-recent_window:]
    prior = records[-(recent_window * 2):-recent_window]

    def _stats_for(group: list[RunTrackerRecord]) -> dict[str, dict[str, object]]:
        return {
            "wave": _compact_stats(record.wave for record in group),
            "coins_per_hour": _compact_stats(record.coins_per_hour for record in group),
            "coins_per_run": _compact_stats(record.coins for record in group),
            "duration_hours": _compact_stats(
                None if record.duration_seconds is None else record.duration_seconds / 3600.0
                for record in group
            ),
            "tracker_game_time_hours": _compact_stats(
                None if record.game_time_seconds is None else record.game_time_seconds / 3600.0
                for record in group
            ),
            "tracker_game_to_real_duration_ratio": _compact_stats(
                _tracker_game_to_real_duration_ratio(record) for record in group
            ),
            "tracker_waves_per_hour": _compact_stats(record.waves_per_hour for record in group),
            "observed_waves_per_hour": _compact_stats(
                _observed_waves_per_hour(record) for record in group
            ),
            "tracker_to_observed_waves_per_hour_ratio": _compact_stats(
                _tracker_to_observed_waves_per_hour_ratio(record) for record in group
            ),
            "observed_enemies_per_wave": _compact_stats(
                _observed_enemies_per_wave(record) for record in group
            ),
            "observed_coins_per_enemy": _compact_stats(
                _observed_coins_per_enemy(record) for record in group
            ),
            "observed_coins_per_wave": _compact_stats(
                _observed_coins_per_wave(record) for record in group
            ),
            "tracker_econ_coin_sources": _tracker_econ_coin_source_summary(group),
            "tracker_coins_from_wave_skip": _compact_stats(
                record.coins_from_wave_skip for record in group
            ),
            "tracker_coins_per_wave": _compact_stats(record.coins_per_wave for record in group),
            "tracker_coins_per_wave_to_observed_ratio": _compact_stats(
                _tracker_coins_per_wave_to_observed_ratio(record) for record in group
            ),
            "tracker_wave_skip_coin_share": _compact_stats(
                _tracker_wave_skip_coin_share(record) for record in group
            ),
            "tracker_wave_skip_coins_per_skipped_wave": _compact_stats(
                _tracker_wave_skip_coins_per_skipped_wave(record) for record in group
            ),
            "observed_cph_from_run_totals": _compact_stats(
                _observed_cph_from_run_totals(record) for record in group
            ),
            "observed_cph_to_tracker_reported_ratio": _compact_stats(
                _observed_cph_to_tracker_reported_ratio(record) for record in group
            ),
            "observed_cph_from_density_components": _compact_stats(
                _observed_cph_from_density_components(record) for record in group
            ),
        }

    recent_stats = _stats_for(recent)
    prior_stats = _stats_for(prior)
    latest = _record_payload(recent[-1]) if recent else None
    metrics = {
        metric: _trend_metric(
            recent=recent_stats[metric],
            prior=prior_stats[metric],
        )
        for metric in recent_stats
    }
    return {
        "status": (
            "recent_and_prior_windows_available"
            if recent and prior
            else "insufficient_prior_window"
            if recent
            else "no_recent_t14_farming_rows"
        ),
        "application": "external_observation_not_account_truth",
        "certification_effect": "none",
        "policy": "prefer_recent_window_for_calibration_when_account_stats_are_improving",
        "recent_window_size": int(recent_window),
        "prior_window_size": int(recent_window),
        "recent_row_count": len(recent),
        "prior_row_count": len(prior),
        "recent_date_range": _record_date_range(recent),
        "prior_date_range": _record_date_range(prior),
        "latest": latest,
        "metrics": metrics,
        "calibration_anchor_hint": {
            "status": "recent_band_available_not_auto_applied" if recent else "not_available",
            "latest_coins_per_hour": None if latest is None else latest.get("coins_per_hour"),
            "recent_median_coins_per_hour": metrics["coins_per_hour"].get("recent", {}).get("median"),
            "prior_median_coins_per_hour": metrics["coins_per_hour"].get("prior", {}).get("median"),
            "recent_to_prior_coins_per_hour_ratio": metrics["coins_per_hour"].get("median_ratio"),
            "interpretation": (
                "Use as calibration evidence for account-improvement drift only; "
                "do not apply as KB truth or certified farming CPH."
            ),
        },
    }


def _record_payload(record: RunTrackerRecord) -> dict[str, object]:
    observed_waves_per_hour = _observed_waves_per_hour(record)
    observed_seconds_per_wave = _observed_seconds_per_wave(record)
    observed_enemies_per_wave = _observed_enemies_per_wave(record)
    observed_coins_per_enemy = _observed_coins_per_enemy(record)
    observed_coins_per_wave = _observed_coins_per_wave(record)
    observed_cph_from_run_totals = _observed_cph_from_run_totals(record)
    observed_cph_from_density_components = _observed_cph_from_density_components(record)
    return {
        "source_row": record.source_row,
        "run_type": record.run_type,
        "tier": record.tier,
        "tier_raw": record.tier_raw,
        "wave": record.wave,
        "duration_hours": None if record.duration_seconds is None else record.duration_seconds / 3600.0,
        "game_time_hours": (
            None if record.game_time_seconds is None else record.game_time_seconds / 3600.0
        ),
        "tracker_game_to_real_duration_ratio": _tracker_game_to_real_duration_ratio(record),
        "coins": record.coins,
        "coins_per_hour": record.coins_per_hour,
        "cells": record.cells,
        "cells_per_hour": record.cells_per_hour,
        "waves_skipped": record.waves_skipped,
        "coins_from_wave_skip": record.coins_from_wave_skip,
        "coins_per_wave": record.coins_per_wave,
        "tracker_coins_per_wave_to_observed_ratio": (
            _tracker_coins_per_wave_to_observed_ratio(record)
        ),
        "most_coins_from_wave_skip": record.most_coins_from_wave_skip,
        "tracker_wave_skip_coin_share": _tracker_wave_skip_coin_share(record),
        "tracker_wave_skip_coins_per_skipped_wave": (
            _tracker_wave_skip_coins_per_skipped_wave(record)
        ),
        "coins_from_death_wave": record.coins_from_death_wave,
        "coins_from_golden_tower": record.coins_from_golden_tower,
        "coins_from_black_hole": record.coins_from_black_hole,
        "coins_from_spotlight": record.coins_from_spotlight,
        "golden_bot_coins_earned": record.golden_bot_coins_earned,
        "coins_from_golden_combo": record.coins_from_golden_combo,
        "total_enemies": record.total_enemies,
        "basic": record.basic,
        "fast": record.fast,
        "tank": record.tank,
        "ranged": record.ranged,
        "boss": record.boss,
        "protector": record.protector,
        "total_elites": record.total_elites,
        "vampires": record.vampires,
        "rays": record.rays,
        "scatters": record.scatters,
        "saboteurs": record.saboteurs,
        "commanders": record.commanders,
        "overcharges": record.overcharges,
        "enemies_per_hour": record.enemies_per_hour,
        "observed_enemies_per_wave": observed_enemies_per_wave,
        "observed_coins_per_enemy": observed_coins_per_enemy,
        "observed_coins_per_wave": observed_coins_per_wave,
        "waves_per_hour": record.waves_per_hour,
        "observed_waves_per_hour": observed_waves_per_hour,
        "tracker_to_observed_waves_per_hour_ratio": (
            _tracker_to_observed_waves_per_hour_ratio(record)
        ),
        "observed_seconds_per_wave": observed_seconds_per_wave,
        "observed_cph_from_run_totals": observed_cph_from_run_totals,
        "observed_cph_to_tracker_reported_ratio": _observed_cph_to_tracker_reported_ratio(
            record
        ),
        "observed_cph_from_density_components": observed_cph_from_density_components,
        "killed_by": record.killed_by,
        "note": record.note,
        "verified": record.verified,
        "run_date": record.run_date,
        "run_time": record.run_time,
        "created_at": record.created_at,
    }


def _observed_waves_per_hour(record: RunTrackerRecord) -> float | None:
    if record.wave is None or record.duration_seconds in (None, 0):
        return None
    return float(record.wave) / (float(record.duration_seconds) / 3600.0)


def _tracker_to_observed_waves_per_hour_ratio(record: RunTrackerRecord) -> float | None:
    observed = _observed_waves_per_hour(record)
    if record.waves_per_hour is None or observed in (None, 0):
        return None
    return float(record.waves_per_hour) / float(observed)


def _tracker_game_to_real_duration_ratio(record: RunTrackerRecord) -> float | None:
    if record.game_time_seconds is None or record.duration_seconds in (None, 0):
        return None
    return float(record.game_time_seconds) / float(record.duration_seconds)


def _observed_seconds_per_wave(record: RunTrackerRecord) -> float | None:
    if record.wave in (None, 0) or record.duration_seconds is None:
        return None
    return float(record.duration_seconds) / float(record.wave)


def _observed_enemies_per_wave(record: RunTrackerRecord) -> float | None:
    if record.total_enemies is None or record.wave in (None, 0):
        return None
    return float(record.total_enemies) / float(record.wave)


def _observed_coins_per_enemy(record: RunTrackerRecord) -> float | None:
    if record.coins is None or record.total_enemies in (None, 0):
        return None
    return float(record.coins) / float(record.total_enemies)


def _observed_coins_per_wave(record: RunTrackerRecord) -> float | None:
    if record.coins is None or record.wave in (None, 0):
        return None
    return float(record.coins) / float(record.wave)


def _tracker_coins_per_wave_to_observed_ratio(record: RunTrackerRecord) -> float | None:
    observed = _observed_coins_per_wave(record)
    if record.coins_per_wave is None or observed in (None, 0):
        return None
    return float(record.coins_per_wave) / float(observed)


def _observed_cph_from_run_totals(record: RunTrackerRecord) -> float | None:
    if record.coins is None or record.duration_seconds in (None, 0):
        return None
    return float(record.coins) / (float(record.duration_seconds) / 3600.0)


def _observed_cph_to_tracker_reported_ratio(record: RunTrackerRecord) -> float | None:
    observed = _observed_cph_from_run_totals(record)
    if observed is None or record.coins_per_hour in (None, 0):
        return None
    return float(observed) / float(record.coins_per_hour)


def _tracker_wave_skip_coin_share(record: RunTrackerRecord) -> float | None:
    if record.coins_from_wave_skip is None or record.coins in (None, 0):
        return None
    return float(record.coins_from_wave_skip) / float(record.coins)


def _tracker_wave_skip_coins_per_skipped_wave(record: RunTrackerRecord) -> float | None:
    if record.coins_from_wave_skip is None or record.waves_skipped in (None, 0):
        return None
    return float(record.coins_from_wave_skip) / float(record.waves_skipped)


def _observed_cph_from_density_components(record: RunTrackerRecord) -> float | None:
    coins_per_enemy = _observed_coins_per_enemy(record)
    enemies_per_wave = _observed_enemies_per_wave(record)
    waves_per_hour = _observed_waves_per_hour(record)
    if coins_per_enemy is None or enemies_per_wave is None or waves_per_hour is None:
        return None
    return float(coins_per_enemy) * float(enemies_per_wave) * float(waves_per_hour)


def _observed_elites_per_wave(record: RunTrackerRecord) -> float | None:
    if record.total_elites is None or record.wave in (None, 0):
        return None
    return float(record.total_elites) / float(record.wave)


def _observed_elites_per_hour(record: RunTrackerRecord) -> float | None:
    if record.total_elites is None or record.duration_seconds in (None, 0):
        return None
    return float(record.total_elites) / (float(record.duration_seconds) / 3600.0)


def _type_tier_summaries(records: list[RunTrackerRecord]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], list[RunTrackerRecord]] = {}
    for record in records:
        groups.setdefault((record.run_type, record.tier_raw), []).append(record)

    summaries: list[dict[str, object]] = []
    for (run_type, tier_raw), group in groups.items():
        ordered = sorted(group, key=_record_sort_key)
        latest = ordered[-1]
        max_wave = max((record.wave or 0 for record in group), default=0)
        max_wave_record = max(group, key=lambda record: record.wave or -1)
        summaries.append(
            {
                "run_type": run_type,
                "tier": latest.tier,
                "tier_raw": tier_raw,
                "row_count": len(group),
                "latest": _record_payload(latest),
                "max_wave": max_wave,
                "max_wave_record": _record_payload(max_wave_record),
                "wave": _compact_stats(record.wave for record in group),
                "coins_per_hour": _compact_stats(record.coins_per_hour for record in group),
                "duration_hours": _compact_stats(
                    None if record.duration_seconds is None else record.duration_seconds / 3600.0
                    for record in group
                ),
                "tracker_game_time_hours": _compact_stats(
                    None if record.game_time_seconds is None else record.game_time_seconds / 3600.0
                    for record in group
                ),
                "tracker_game_to_real_duration_ratio": _compact_stats(
                    _tracker_game_to_real_duration_ratio(record) for record in group
                ),
                "observed_waves_per_hour": _compact_stats(
                    _observed_waves_per_hour(record) for record in group
                ),
                "tracker_waves_per_hour": _compact_stats(
                    record.waves_per_hour for record in group
                ),
                "tracker_to_observed_waves_per_hour_ratio": _compact_stats(
                    _tracker_to_observed_waves_per_hour_ratio(record) for record in group
                ),
                "observed_seconds_per_wave": _compact_stats(
                    _observed_seconds_per_wave(record) for record in group
                ),
                "observed_enemies_per_wave": _compact_stats(
                    _observed_enemies_per_wave(record) for record in group
                ),
                "observed_coins_per_enemy": _compact_stats(
                    _observed_coins_per_enemy(record) for record in group
                ),
                "observed_coins_per_wave": _compact_stats(
                    _observed_coins_per_wave(record) for record in group
                ),
                "tracker_econ_coin_sources": _tracker_econ_coin_source_summary(group),
                "tracker_coins_from_wave_skip": _compact_stats(
                    record.coins_from_wave_skip for record in group
                ),
                "tracker_coins_per_wave": _compact_stats(
                    record.coins_per_wave for record in group
                ),
                "tracker_coins_per_wave_to_observed_ratio": _compact_stats(
                    _tracker_coins_per_wave_to_observed_ratio(record) for record in group
                ),
                "tracker_wave_skip_coin_share": _compact_stats(
                    _tracker_wave_skip_coin_share(record) for record in group
                ),
                "tracker_wave_skip_coins_per_skipped_wave": _compact_stats(
                    _tracker_wave_skip_coins_per_skipped_wave(record) for record in group
                ),
                "observed_cph_from_run_totals": _compact_stats(
                    _observed_cph_from_run_totals(record) for record in group
                ),
                "observed_cph_to_tracker_reported_ratio": _compact_stats(
                    _observed_cph_to_tracker_reported_ratio(record) for record in group
                ),
                "observed_cph_from_density_components": _compact_stats(
                    _observed_cph_from_density_components(record) for record in group
                ),
                "tracker_enemy_composition": _tracker_enemy_composition_summary(group),
            }
        )
    return sorted(
        summaries,
        key=lambda item: (
            str(item["run_type"]),
            int(item["tier"]) if item.get("tier") is not None else 999,
            str(item["tier_raw"]),
        ),
    )


def summarize_run_tracker_records(records: list[RunTrackerRecord], *, recent_window: int = 10) -> dict[str, object]:
    ordered = sorted(records, key=_record_sort_key)
    type_counts = Counter(record.run_type for record in records)
    tier_counts = Counter(record.tier_raw or "Unknown" for record in records)
    numeric_t14_farming = [
        record
        for record in ordered
        if record.run_type == "Farming"
        and record.tier == 14
        and record.wave is not None
        and record.duration_seconds is not None
        and record.coins_per_hour is not None
    ]
    recent_t14_farming = numeric_t14_farming[-recent_window:]
    farming_t14_trend = _farming_t14_recent_trend(
        numeric_t14_farming,
        recent_window=recent_window,
    )

    return {
        "source": "tower_run_tracker_csv",
        "application": "external_observation_not_account_truth",
        "calibration_policy": {
            "status": "evidence_available_not_auto_applied",
            "stats_trend_policy": "prefer_recency_bands_over_lifetime_aggregate_when_account_stats_are_improving",
            "formula_policy": "do_not_certify_boss_wave_or_farming_econ_formula_from_tracker_rows_alone",
        },
        "row_count": len(records),
        "date_range": {
            "min_run_date": ordered[0].run_date if ordered else None,
            "max_run_date": ordered[-1].run_date if ordered else None,
        },
        "run_type_counts": dict(sorted(type_counts.items())),
        "tier_counts": dict(sorted(tier_counts.items())),
        "type_tier_summaries": _type_tier_summaries(records),
        "farming_t14_recent_trend": farming_t14_trend,
        "farming_t14_recent": {
            "definition": f"latest_{recent_window}_numeric_t14_farming_rows",
            "row_count": len(recent_t14_farming),
            "latest": _record_payload(recent_t14_farming[-1]) if recent_t14_farming else None,
            "wave": _compact_stats(record.wave for record in recent_t14_farming),
            "duration_hours": _compact_stats(
                None if record.duration_seconds is None else record.duration_seconds / 3600.0
                for record in recent_t14_farming
            ),
            "tracker_game_time_hours": _compact_stats(
                None if record.game_time_seconds is None else record.game_time_seconds / 3600.0
                for record in recent_t14_farming
            ),
            "tracker_game_to_real_duration_ratio": _compact_stats(
                _tracker_game_to_real_duration_ratio(record)
                for record in recent_t14_farming
            ),
            "coins_per_hour": _compact_stats(record.coins_per_hour for record in recent_t14_farming),
            "coins_per_run": _compact_stats(record.coins for record in recent_t14_farming),
            "waves_skipped": _compact_stats(record.waves_skipped for record in recent_t14_farming),
            "total_enemies": _compact_stats(record.total_enemies for record in recent_t14_farming),
            "total_elites": _compact_stats(record.total_elites for record in recent_t14_farming),
            "tracker_waves_per_hour": _compact_stats(record.waves_per_hour for record in recent_t14_farming),
            "observed_waves_per_hour": _compact_stats(
                _observed_waves_per_hour(record) for record in recent_t14_farming
            ),
            "tracker_to_observed_waves_per_hour_ratio": _compact_stats(
                _tracker_to_observed_waves_per_hour_ratio(record)
                for record in recent_t14_farming
            ),
            "observed_seconds_per_wave": _compact_stats(
                _observed_seconds_per_wave(record) for record in recent_t14_farming
            ),
            "tracker_enemies_per_hour": _compact_stats(record.enemies_per_hour for record in recent_t14_farming),
            "observed_enemies_per_wave": _compact_stats(
                _observed_enemies_per_wave(record) for record in recent_t14_farming
            ),
            "observed_coins_per_enemy": _compact_stats(
                _observed_coins_per_enemy(record) for record in recent_t14_farming
            ),
            "observed_coins_per_wave": _compact_stats(
                _observed_coins_per_wave(record) for record in recent_t14_farming
            ),
            "tracker_econ_coin_sources": _tracker_econ_coin_source_summary(
                recent_t14_farming
            ),
            "tracker_coins_from_wave_skip": _compact_stats(
                record.coins_from_wave_skip for record in recent_t14_farming
            ),
            "tracker_coins_per_wave": _compact_stats(
                record.coins_per_wave for record in recent_t14_farming
            ),
            "tracker_coins_per_wave_to_observed_ratio": _compact_stats(
                _tracker_coins_per_wave_to_observed_ratio(record)
                for record in recent_t14_farming
            ),
            "tracker_wave_skip_coin_share": _compact_stats(
                _tracker_wave_skip_coin_share(record) for record in recent_t14_farming
            ),
            "tracker_wave_skip_coins_per_skipped_wave": _compact_stats(
                _tracker_wave_skip_coins_per_skipped_wave(record)
                for record in recent_t14_farming
            ),
            "observed_cph_from_run_totals": _compact_stats(
                _observed_cph_from_run_totals(record) for record in recent_t14_farming
            ),
            "observed_cph_to_tracker_reported_ratio": _compact_stats(
                _observed_cph_to_tracker_reported_ratio(record)
                for record in recent_t14_farming
            ),
            "observed_cph_from_density_components": _compact_stats(
                _observed_cph_from_density_components(record) for record in recent_t14_farming
            ),
            "tracker_enemy_composition": _tracker_enemy_composition_summary(
                recent_t14_farming
            ),
            "observed_elites_per_hour": _compact_stats(
                _observed_elites_per_hour(record) for record in recent_t14_farming
            ),
            "observed_elites_per_wave": _compact_stats(
                _observed_elites_per_wave(record) for record in recent_t14_farming
            ),
        },
    }


def summarize_run_tracker_csv(path: Path) -> dict[str, object]:
    records = parse_run_tracker_csv(path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
    missing_required_columns = [column for column in _REQUIRED_COLUMNS if column not in columns]
    summary = summarize_run_tracker_records(records)
    summary["input_schema"] = {
        "column_count": len(columns),
        "required_columns": list(_REQUIRED_COLUMNS),
        "missing_required_columns": missing_required_columns,
    }
    summary["input_path"] = str(path)
    return summary
