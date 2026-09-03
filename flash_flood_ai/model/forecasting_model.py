"""
forecasting_model.py — Multi-Horizon Temporal Forecasting
==========================================================

Forecasts risk at 15, 30, 60, and 120 minute horizons.
Uses lag/trend features with Random Forest when trained, or
linear trend extrapolation as baseline fallback.

Computes estimated time-to-danger thresholds.
"""

from __future__ import annotations

import math
import os
from typing import Any

import numpy as np

from model import config
from model.feature_engineering import compute_features, normalize_features
from model.risk_engine import predict_risk


# ── Public interface ───────────────────────────────────────────────────────

def forecast_risk(
    timeseries: list[dict[str, Any]],
    horizons: list[int] | None = None,
    upstream_data: dict[str, Any] | None = None,
    population_data: dict[str, Any] | None = None,
    model_mode: str | None = None,
) -> dict:
    """Forecast risk at multiple future horizons.

    Parameters
    ----------
    timeseries : list[dict]
        Chronologically ordered observations (oldest first, 15-min intervals).
    horizons : list[int] | None
        Forecast horizons in minutes (default: [15, 30, 60, 120]).
    upstream_data : dict | None
        Current upstream sensor data.
    population_data : dict | None
        Population/vulnerability data.
    model_mode : str | None
        Override for ``config.MODEL_MODE``.

    Returns
    -------
    dict
        ``current_risk``  – current risk score
        ``forecast``      – {horizon_key: predicted_risk}
        ``estimated_time_to_high_risk_min`` – int | None
        ``estimated_time_to_critical_min``  – int | None
        ``method`` – "trend_extrapolation" or "ml_forecast"
    """
    horizons = horizons or config.FORECAST_HORIZONS

    if not timeseries or len(timeseries) < 2:
        return _empty_forecast(horizons)

    # Current risk
    current = timeseries[-1]
    history = timeseries[:-1] if len(timeseries) > 1 else []
    current_result = predict_risk(
        current, history, upstream_data, population_data, model_mode,
    )
    current_risk = current_result["risk_score"]

    # Forecast at each horizon
    forecast: dict[str, float] = {}
    forecast_points: list[tuple[int, float]] = [(0, current_risk)]

    for h in sorted(horizons):
        predicted = _forecast_at_horizon(timeseries, h, upstream_data, population_data, model_mode)
        key = f"{h}_min"
        forecast[key] = round(predicted, 4)
        forecast_points.append((h, predicted))

    # Time-to-danger estimation
    t_high = _interpolate_threshold(forecast_points, 0.55)
    t_critical = _interpolate_threshold(forecast_points, 0.75)

    return {
        "current_risk": round(current_risk, 4),
        "forecast": forecast,
        "estimated_time_to_high_risk_min": t_high,
        "estimated_time_to_critical_min": t_critical,
        "method": "trend_extrapolation",
    }


# ── Internal helpers ──────────────────────────────────────────────────────

def _forecast_at_horizon(
    timeseries: list[dict[str, Any]],
    horizon_min: int,
    upstream_data: dict[str, Any] | None,
    population_data: dict[str, Any] | None,
    model_mode: str | None,
) -> float:
    """Forecast risk at a single future horizon using trend extrapolation.

    Extrapolates current trends (rainfall rate-of-change, river rise rate,
    soil saturation change) forward by *horizon_min* minutes, constructs a
    synthetic future observation, and runs it through the risk engine.
    """
    current = timeseries[-1]
    features = compute_features(timeseries, upstream_data)

    # Number of 15-min steps into the future
    steps = horizon_min / 15.0

    # Extrapolate key variables
    future = dict(current)

    # Rainfall: use rate-of-change
    rain_rate = features.get("rainfall_change_15min") or 0.0
    rain_accel = features.get("rainfall_acceleration") or 0.0
    current_rain = _sf(current.get("rainfall_mm_hr", 0))
    future_rain = current_rain + rain_rate * steps + 0.5 * rain_accel * steps ** 2
    future["rainfall_mm_hr"] = max(0.0, future_rain)

    # River level: use rise rate
    river_rate = features.get("river_rise_rate") or 0.0
    river_accel = features.get("river_rise_acceleration") or 0.0
    current_river = _sf(current.get("river_level_m", 0))
    future_river = current_river + river_rate * steps + 0.5 * river_accel * steps ** 2
    future["river_level_m"] = max(0.0, future_river)

    # Soil saturation: use change rate
    soil_change = features.get("soil_saturation_change") or 0.0
    current_soil = _sf(current.get("soil_saturation", 0))
    future_soil = current_soil + soil_change * steps
    future["soil_saturation"] = max(0.0, min(1.0, future_soil))

    # Run through risk engine with the synthetic future observation
    result = predict_risk(
        future, timeseries, upstream_data, population_data, model_mode,
    )
    return result["risk_score"]


def _interpolate_threshold(
    points: list[tuple[int, float]],
    threshold: float,
) -> int | None:
    """Linear interpolation to find when risk crosses *threshold*.

    Parameters
    ----------
    points : list[(time_min, risk)]
        Sorted by time.
    threshold : float
        Risk threshold to find crossing for.

    Returns
    -------
    int | None
        Estimated minutes until threshold is crossed, or ``None``.
    """
    # Already above threshold
    if points and points[0][1] >= threshold:
        return 0

    for i in range(1, len(points)):
        t0, r0 = points[i - 1]
        t1, r1 = points[i]
        if r0 < threshold <= r1:
            # Linear interpolation
            if r1 == r0:
                return t0
            frac = (threshold - r0) / (r1 - r0)
            t_cross = t0 + frac * (t1 - t0)
            return int(round(t_cross))

    return None  # threshold never crossed within forecast window


def _empty_forecast(horizons: list[int]) -> dict:
    """Return an empty forecast when insufficient data is available."""
    return {
        "current_risk": None,
        "forecast": {f"{h}_min": None for h in horizons},
        "estimated_time_to_high_risk_min": None,
        "estimated_time_to_critical_min": None,
        "method": "insufficient_data",
    }


def _sf(val: Any) -> float:
    """Safe float, default 0."""
    if val is None:
        return 0.0
    try:
        f = float(val)
        return 0.0 if math.isnan(f) else f
    except (TypeError, ValueError):
        return 0.0
