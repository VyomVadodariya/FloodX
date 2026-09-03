"""
uncertainty.py — Confidence, Data Quality & Model Uncertainty
==============================================================

Estimates how much trust should be placed in each prediction.
Combines data quality, feature completeness, model uncertainty
(RF tree variance), and signal agreement.
"""

from __future__ import annotations

import math
from typing import Any

from model.config import CONFIDENCE_WEIGHTS, ML_FEATURE_NAMES


# ── Public interface ───────────────────────────────────────────────────────

def estimate_confidence(
    point: dict[str, Any],
    features: dict[str, float | None],
    data_quality_report: dict | None = None,
    model_predictions: list[float] | None = None,
) -> dict:
    """Produce a structured confidence / uncertainty report.

    Parameters
    ----------
    point : dict
        Raw observation.
    features : dict
        Engineered features (some may be ``None``).
    data_quality_report : dict | None
        Output of ``AnomalyDetector.validate()``.
    model_predictions : list[float] | None
        Per-tree predictions from the Random Forest (used for
        model-uncertainty estimation).

    Returns
    -------
    dict
        ``confidence``          – overall [0, 1]
        ``data_quality_score``  – [0, 1]
        ``feature_completeness``– [0, 1]
        ``model_uncertainty``   – [0, 1] (0 = certain, 1 = very uncertain)
        ``signal_agreement``    – [0, 1]
        ``components``          – dict of individual scores
    """
    # -- 1. Data quality & Sensor Reliability ------------------------------
    if data_quality_report:
        dq = data_quality_report.get("data_quality_score", 1.0)
        sr_dict = data_quality_report.get("sensor_reliability", {})
        if sr_dict:
            sr = sum(s.get("reliability_score", 1.0) for s in sr_dict.values()) / len(sr_dict)
        else:
            sr = 1.0
    else:
        dq = 1.0
        sr = 1.0

    # -- 2. Feature completeness -------------------------------------------
    fc = _feature_completeness(features)

    # -- 3. Model uncertainty (RF tree variance) ---------------------------
    mu = _model_uncertainty(model_predictions)

    # -- 4. Signal agreement -----------------------------------------------
    sa = _signal_agreement(features)

    # -- Weighted combination -----------------------------------------------
    w = CONFIDENCE_WEIGHTS
    # model_uncertainty is inverted: high uncertainty → low confidence
    raw = (
        w["data_quality"] * dq
        + w["sensor_reliability"] * sr
        + w["feature_completeness"] * fc
        + w["model_uncertainty"] * (1.0 - mu)
        + w["signal_agreement"] * sa
    )
    confidence = max(0.0, min(1.0, raw))

    return {
        "confidence": round(confidence, 4),
        "data_quality_score": round(dq, 4),
        "sensor_reliability_score": round(sr, 4),
        "feature_completeness": round(fc, 4),
        "model_uncertainty": round(mu, 4),
        "signal_agreement": round(sa, 4),
        "components": {
            "data_quality": round(dq, 4),
            "sensor_reliability": round(sr, 4),
            "feature_completeness": round(fc, 4),
            "model_uncertainty": round(mu, 4),
            "signal_agreement": round(sa, 4),
        },
    }


# ── Internal helpers ──────────────────────────────────────────────────────

def _feature_completeness(features: dict[str, float | None]) -> float:
    """Fraction of ML feature fields that are non-None / non-NaN."""
    total = 0
    present = 0
    for key in ML_FEATURE_NAMES:
        total += 1
        val = features.get(key)
        if val is not None and not (isinstance(val, float) and math.isnan(val)):
            present += 1
    return present / max(total, 1)


def _model_uncertainty(predictions: list[float] | None) -> float:
    """Standard deviation of per-tree predictions, normalized to [0, 1].

    Higher std → higher uncertainty.
    """
    if not predictions or len(predictions) < 2:
        return 0.5  # unknown → moderate uncertainty
    mean = sum(predictions) / len(predictions)
    var = sum((p - mean) ** 2 for p in predictions) / len(predictions)
    std = math.sqrt(var)
    # Normalize: std of 0.25 (on a 0-1 scale) is considered very uncertain
    return min(1.0, std / 0.25)


def _signal_agreement(features: dict[str, float | None]) -> float:
    """Check whether multiple independent signals agree on the trend.

    If rainfall is rising, river is rising, and soil is saturating — the
    signals agree.  Conflicting signals reduce agreement.
    """
    signals: list[float] = []

    # Direction indicators: positive = worsening, negative = improving
    for field, direction in [
        ("rainfall_change_30min", 1.0),
        ("river_rise_rate", 1.0),
        ("soil_saturation_change", 1.0),
    ]:
        val = features.get(field)
        if val is not None and not (isinstance(val, float) and math.isnan(val)):
            signals.append(1.0 if val * direction >= 0 else -1.0)

    if len(signals) < 2:
        return 0.5  # insufficient information

    # Agreement = fraction of signals pointing the same direction
    positive = sum(1 for s in signals if s > 0)
    negative = len(signals) - positive
    dominant = max(positive, negative)
    return dominant / len(signals)
