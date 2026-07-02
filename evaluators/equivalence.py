"""Enemy pressure equivalence utilities."""
from __future__ import annotations

import csv, json, math, re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

_SUFFIX_EXPONENTS: dict[str, int] = {
    "": 0, "K": 3, "M": 6, "B": 9, "T": 12, "q": 15, "Q": 18,
    "s": 21, "S": 24, "O": 27, "N": 30, "D": 33,
}
_exp = 36
for _a in "abcdefghijklmnopqrstuvwxyz":
    for _b in "abcdefghijklmnopqrstuvwxyz":
        _SUFFIX_EXPONENTS[f"{_a}{_b}"] = _exp
        _exp += 3
_DAMAGE_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]*)\s*$")


def parse_damage_label(label: str) -> float:
    """Parse The Tower notation: 100N=1e32, 1D=1e33, 1aa=1e36."""
    match = _DAMAGE_RE.match(label)
    if not match:
        raise ValueError(f"Invalid damage label: {label!r}")
    suffix = match.group(2)
    if suffix not in _SUFFIX_EXPONENTS:
        raise ValueError(f"Unknown damage suffix {suffix!r}")
    return float(match.group(1)) * (10 ** _SUFFIX_EXPONENTS[suffix])


def format_damage_value(value: float, *, precision: int = 3) -> str:
    if value < 0 or not math.isfinite(value):
        raise ValueError("value must be finite and non-negative")
    if value == 0:
        return "0"
    suffix, exp = "", 0
    for candidate, candidate_exp in sorted(_SUFFIX_EXPONENTS.items(), key=lambda item: item[1]):
        if value >= 10 ** candidate_exp:
            suffix, exp = candidate, candidate_exp
        else:
            break
    return f"{value / (10 ** exp):.{precision}g}{suffix}"


@dataclass(frozen=True)
class EnemyCurve:
    """Strictly increasing wave->enemy-value curve using log-linear interpolation."""

    surface: str
    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("EnemyCurve requires at least two points")
        prev_wave, prev_value = -math.inf, -math.inf
        for wave, value in self.points:
            if not math.isfinite(wave) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid point {(wave, value)!r}")
            if wave <= prev_wave or value <= prev_value:
                raise ValueError("EnemyCurve points must strictly increase")
            prev_wave, prev_value = wave, value

    @classmethod
    def from_wide_csv(cls, path: Path | str, surface: str) -> "EnemyCurve":
        with Path(path).open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            if "wave_actual" not in fields or surface not in fields:
                raise ValueError(f"Missing wave_actual or {surface!r} in {path}")
            points: list[tuple[float, float]] = []
            for row in reader:
                raw = row.get(surface)
                if raw in (None, "", "inf", "Infinity"):
                    continue
                value = float(raw)
                if math.isfinite(value) and value > 0:
                    points.append((float(row["wave_actual"]), value))
        return cls(surface, tuple(points))

    def value_at_wave(self, wave: float) -> float:
        (x0, y0), (x1, y1) = self._bounds_for_wave(wave)
        return _interp_log_y(x=wave, x0=x0, y0=y0, x1=x1, y1=y1)

    def wave_for_value(self, value: float) -> float:
        if value <= 0 or not math.isfinite(value):
            raise ValueError("value must be positive and finite")
        (x0, y0), (x1, y1) = self._bounds_for_value(value)
        return _interp_x_from_log_y(y=value, x0=x0, y0=y0, x1=x1, y1=y1)

    def _bounds_for_wave(self, wave: float) -> tuple[tuple[float, float], tuple[float, float]]:
        if wave <= self.points[0][0]:
            return self.points[0], self.points[1]
        if wave >= self.points[-1][0]:
            return self.points[-2], self.points[-1]
        for left, right in zip(self.points, self.points[1:]):
            if left[0] <= wave <= right[0]:
                return left, right
        raise RuntimeError("unreachable wave bounds")

    def _bounds_for_value(self, value: float) -> tuple[tuple[float, float], tuple[float, float]]:
        if value <= self.points[0][1]:
            return self.points[0], self.points[1]
        if value >= self.points[-1][1]:
            return self.points[-2], self.points[-1]
        for left, right in zip(self.points, self.points[1:]):
            if left[1] <= value <= right[1]:
                return left, right
        raise RuntimeError("unreachable value bounds")


def _interp_log_y(*, x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    return 10 ** (math.log10(y0) + ((x - x0) / (x1 - x0)) * (math.log10(y1) - math.log10(y0)))


def _interp_x_from_log_y(*, y: float, x0: float, y0: float, x1: float, y1: float) -> float:
    return x0 + ((math.log10(y) - math.log10(y0)) / (math.log10(y1) - math.log10(y0))) * (x1 - x0)


def _validate_skip(value: float, name: str = "skip_chance") -> None:
    if not math.isfinite(value) or not 0 <= value < 1:
        raise ValueError(f"{name} must be a finite fraction in [0, 1)")


@dataclass(frozen=True)
class FixedSkipProfile:
    """Explicit final ELS profile. EHLS=health axis; EALS=damage axis."""

    ehls: float = 0.0
    eals: float = 0.0

    def __post_init__(self) -> None:
        _validate_skip(self.ehls, "ehls")
        _validate_skip(self.eals, "eals")


def effective_wave_from_displayed_wave(displayed_wave: float, skip_chance: float) -> float:
    _validate_skip(skip_chance)
    if displayed_wave < 1:
        raise ValueError("displayed_wave must be >= 1")
    return 1 + (displayed_wave - 1) * (1 - skip_chance)


def displayed_wave_from_effective_wave(effective_wave: float, skip_chance: float) -> float:
    _validate_skip(skip_chance)
    if effective_wave < 1:
        raise ValueError("effective_wave must be >= 1")
    return 1 + (effective_wave - 1) / (1 - skip_chance)


def integrate_effective_wave(displayed_wave: int, skip_chance_by_wave: Callable[[int], float]) -> float:
    if displayed_wave < 1:
        raise ValueError("displayed_wave must be >= 1")
    effective = 1.0
    for wave in range(1, displayed_wave):
        chance = skip_chance_by_wave(wave)
        _validate_skip(chance, f"skip_chance_by_wave({wave})")
        effective += 1 - chance
    return effective


@dataclass(frozen=True)
class SurfaceCalibration:
    """Empirical surface-only calibration. Does not mutate raw tier curves."""

    surface: str
    budget_multiplier: float
    source: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.budget_multiplier) or self.budget_multiplier <= 0:
            raise ValueError("budget_multiplier must be positive and finite")

    @classmethod
    def from_anchor(cls, *, surface: str, curve: EnemyCurve, damage_label: str, displayed_wave: float, source: str = "empirical_anchor") -> "SurfaceCalibration":
        return cls(
            surface=surface,
            budget_multiplier=curve.value_at_wave(displayed_wave) / parse_damage_label(damage_label),
            source=f"{source}:{damage_label}->{displayed_wave:g}",
        )


@dataclass(frozen=True)
class EquivalenceResult:
    damage_label: str
    raw_damage_value: float
    surface: str
    axis: str
    raw_effective_wave: float
    displayed_wave: float
    skip_chance: float
    budget_multiplier: float = 1.0
    calibration_source: str | None = None

    def to_row(self) -> dict[str, float | str | None]:
        return {
            "damage_label": self.damage_label,
            "raw_damage_value": self.raw_damage_value,
            "surface": self.surface,
            "axis": self.axis,
            "raw_effective_wave": self.raw_effective_wave,
            "displayed_wave": self.displayed_wave,
            "skip_chance": self.skip_chance,
            "budget_multiplier": self.budget_multiplier,
            "calibration_source": self.calibration_source,
        }


def equivalent_wave_for_budget(*, damage_label: str, curve: EnemyCurve, axis: str = "health", skip_chance: float = 0.0, calibration: SurfaceCalibration | None = None) -> EquivalenceResult:
    if calibration is not None and calibration.surface != curve.surface:
        raise ValueError("calibration surface must match curve surface")
    raw_damage = parse_damage_label(damage_label)
    multiplier = calibration.budget_multiplier if calibration else 1.0
    raw_effective_wave = curve.wave_for_value(raw_damage * multiplier)
    displayed_wave = displayed_wave_from_effective_wave(raw_effective_wave, skip_chance)
    return EquivalenceResult(
        damage_label=damage_label,
        raw_damage_value=raw_damage,
        surface=curve.surface,
        axis=axis,
        raw_effective_wave=raw_effective_wave,
        displayed_wave=displayed_wave,
        skip_chance=skip_chance,
        budget_multiplier=multiplier,
        calibration_source=calibration.source if calibration else None,
    )


def build_equivalence_table(*, damage_labels: Sequence[str], curves: Mapping[str, EnemyCurve], axis: str, skip_chances: Mapping[str, float] | None = None, calibrations: Mapping[str, SurfaceCalibration] | None = None) -> list[EquivalenceResult]:
    rows: list[EquivalenceResult] = []
    for label in damage_labels:
        for surface, curve in curves.items():
            rows.append(equivalent_wave_for_budget(
                damage_label=label,
                curve=curve,
                axis=axis,
                skip_chance=(skip_chances or {}).get(surface, 0.0),
                calibration=(calibrations or {}).get(surface),
            ))
    return rows


def pivot_displayed_waves(rows: Iterable[EquivalenceResult]) -> list[dict[str, str | int]]:
    pivot: dict[str, dict[str, str | int]] = {}
    for result in rows:
        row = pivot.setdefault(result.damage_label, {"damage_label": result.damage_label})
        row[result.surface] = int(round(result.displayed_wave))
    return list(pivot.values())


def rows_to_csv_text(rows: Iterable[Mapping[str, object]]) -> str:
    rows = list(rows)
    if not rows:
        return ""
    fieldnames: list[str] = []
    for row in rows:
        fieldnames.extend(key for key in row if key not in fieldnames)
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def rows_to_json_text(rows: Iterable[Mapping[str, object]]) -> str:
    return json.dumps(list(rows), indent=2)
