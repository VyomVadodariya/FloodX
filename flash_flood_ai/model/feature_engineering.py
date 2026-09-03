"""
feature_engineering.py — Spatiotemporal Feature Engineering
============================================================

Computes rolling windows, rates, accelerations, and upstream-aware features
from time-series sensor data.  All features are deterministic and testable.
"""

from __future__ import annotations

import math
from typing import Any

from model.config import NORMALIZATION_BOUNDS


# ── Public interface ───────────────────────────────────────────────────────

def compute_features(
    timeseries: list[dict[str, Any]],
    upstream_data: dict[str, Any] | None = None,
) -> dict[str, float | None]:
    """Compute all engineered features from a location's time-series.

    Parameters
    ----------
    timeseries : list[dict]
        Chronologically ordered observations (oldest → newest).
        Each dict must contain at least ``rainfall_mm_hr``, ``river_level_m``,
        ``soil_saturation``.  Interval is assumed 15 min unless a ``timestamp``
        field is present.
    upstream_data : dict | None
        Optional upstream readings (``upstream_rainfall``, etc.).

    Returns
    -------
    dict
        Engineered feature dict.  Missing / un-computable features are ``None``.
    """
    if not timeseries:
        return _empty_features()

    current = timeseries[-1]
    features: dict[str, float | None] = {}

    # -- Pass-through static / current fields --------------------------------
    for field in (
        "rainfall_mm_hr", "river_level_m", "slope_deg",
        "soil_saturation", "historical_incident_density",
        "population_exposure",
    ):
        features[field] = _sf(current.get(field))

    # -- Rolling rainfall windows -------------------------------------------
    features["rainfall_15min"] = _mean_window(timeseries, "rainfall_mm_hr", 1)
    features["rainfall_30min"] = _mean_window(timeseries, "rainfall_mm_hr", 2)
    features["rainfall_1hr"]   = _mean_window(timeseries, "rainfall_mm_hr", 4)
    features["rainfall_3hr"]   = _mean_window(timeseries, "rainfall_mm_hr", 12)
    features["rainfall_6hr"]   = _mean_window(timeseries, "rainfall_mm_hr", 24)

    # -- Rainfall accumulations (sum, not mean) -----------------------------
    features["rainfall_accumulation_1hr"] = _sum_window(timeseries, "rainfall_mm_hr", 4)
    features["rainfall_accumulation_3hr"] = _sum_window(timeseries, "rainfall_mm_hr", 12)
    features["rainfall_accumulation_6hr"] = _sum_window(timeseries, "rainfall_mm_hr", 24)

    # -- Rainfall change & acceleration -------------------------------------
    features["rainfall_change_15min"] = _delta(timeseries, "rainfall_mm_hr", 1)
    features["rainfall_change_30min"] = _delta(timeseries, "rainfall_mm_hr", 2)
    features["rainfall_acceleration"]  = _acceleration(timeseries, "rainfall_mm_hr", 1)

    # -- River-level change & rate ------------------------------------------
    features["river_level_change_15min"] = _delta(timeseries, "river_level_m", 1)
    features["river_level_change_30min"] = _delta(timeseries, "river_level_m", 2)
    features["river_level_change_1hr"]   = _delta(timeseries, "river_level_m", 4)
    features["river_rise_rate"]          = _delta(timeseries, "river_level_m", 1)  # m/15min
    features["river_rise_acceleration"]  = _acceleration(timeseries, "river_level_m", 1)

    # -- Soil saturation change ---------------------------------------------
    features["soil_saturation_change"] = _delta(timeseries, "soil_saturation", 1)

    # -- Upstream features (graceful fallback) ------------------------------
    if upstream_data:
        features["upstream_rainfall"]        = _sf(upstream_data.get("upstream_rainfall"))
        features["upstream_river_level"]     = _sf(upstream_data.get("upstream_river_level"))
        features["upstream_river_rise_rate"] = _sf(upstream_data.get("upstream_river_rise_rate"))
        features["upstream_rainfall_accumulation"] = _sf(
            upstream_data.get("upstream_rainfall_accumulation")
        )
        features["upstream_distance_km"] = _sf(upstream_data.get("upstream_distance_km"))
        features["estimated_travel_time_min"] = _sf(upstream_data.get("estimated_travel_time_min"))
    else:
        features["upstream_rainfall"]        = None
        features["upstream_river_level"]     = None
        features["upstream_river_rise_rate"] = None
        features["upstream_rainfall_accumulation"] = None
        features["upstream_distance_km"] = None
        features["estimated_travel_time_min"] = None

    return features


def normalize(value: float | None, field: str) -> float:
    """Linearly normalize *value* to [0, 1] using configured bounds.

    Returns 0.0 for ``None`` / NaN.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    lo, hi = NORMALIZATION_BOUNDS.get(field, (0.0, 1.0))
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def normalize_features(features: dict[str, float | None]) -> dict[str, float]:
    """Normalize all features in *features* that have configured bounds."""
    normed: dict[str, float] = {}
    for key, val in features.items():
        if key in NORMALIZATION_BOUNDS:
            normed[key] = normalize(val, key)
        else:
            normed[key] = val if val is not None else 0.0
    return normed


# ── Helpers ────────────────────────────────────────────────────────────────

def _sf(val: Any) -> float | None:
    """Safe-float conversion."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _get_field(ts: list[dict], field: str, idx: int) -> float | None:
    """Get a float value from ``ts[idx][field]``, or ``None``."""
    if 0 <= idx < len(ts):
        return _sf(ts[idx].get(field))
    return None


def _mean_window(ts: list[dict], field: str, n_steps: int) -> float | None:
    """Mean of the last *n_steps* values (including current)."""
    start = max(0, len(ts) - n_steps)
    vals = [_sf(ts[i].get(field)) for i in range(start, len(ts))]
    valid = [v for v in vals if v is not None]
    return sum(valid) / len(valid) if valid else None


def _sum_window(ts: list[dict], field: str, n_steps: int) -> float | None:
    """Sum of the last *n_steps* values (including current).

    Each value represents an *intensity* (mm/hr) at a 15-min tick, so the
    accumulation is ``sum(intensity * 0.25)`` (quarter-hour fractions).
    """
    start = max(0, len(ts) - n_steps)
    vals = [_sf(ts[i].get(field)) for i in range(start, len(ts))]
    valid = [v for v in vals if v is not None]
    if not valid:
        return None
    # Convert intensity (mm/hr) to accumulation (mm) over 15-min intervals
    return sum(v * 0.25 for v in valid)


def _delta(ts: list[dict], field: str, lag: int) -> float | None:
    """Difference between current and *lag* steps ago."""
    if len(ts) < lag + 1:
        return None
    cur = _sf(ts[-1].get(field))
    prev = _sf(ts[-1 - lag].get(field))
    if cur is None or prev is None:
        return None
    return cur - prev


def _acceleration(ts: list[dict], field: str, lag: int) -> float | None:
    """Second derivative — change of the rate of change."""
    if len(ts) < 2 * lag + 1:
        return None
    d1 = _delta(ts[:-lag], field, lag) if len(ts) > lag else None  # previous rate
    d2 = _delta(ts, field, lag)  # current rate
    if d1 is None or d2 is None:
        return None
    return d2 - d1


def _empty_features() -> dict[str, float | None]:
    """Return a feature dict with all values set to ``None``."""
    keys = [
        "rainfall_mm_hr", "river_level_m", "slope_deg", "soil_saturation",
        "historical_incident_density", "population_exposure",
        "rainfall_15min", "rainfall_30min", "rainfall_1hr", "rainfall_3hr",
        "rainfall_6hr", "rainfall_accumulation_1hr", "rainfall_accumulation_3hr",
        "rainfall_accumulation_6hr", "rainfall_change_15min",
        "rainfall_change_30min", "rainfall_acceleration",
        "river_level_change_15min", "river_level_change_30min",
        "river_level_change_1hr", "river_rise_rate", "river_rise_acceleration",
        "soil_saturation_change",
        "upstream_rainfall", "upstream_river_level",
        "upstream_river_rise_rate", "upstream_rainfall_accumulation",
        "upstream_distance_km", "estimated_travel_time_min",
    ]
    return {k: None for k in keys}
