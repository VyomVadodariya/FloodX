"""
risk_engine.py — Unified Risk Prediction Engine
=================================================

Provides ``predict_risk(point, history, upstream_data, population_data)``
which dispatches to either the explainable baseline or the trained ML model
based on ``config.MODEL_MODE``.

The frontend never needs to know which model is running.
"""

from __future__ import annotations

import math
import os
from typing import Any

import numpy as np

from model import config
from model.anomaly_detector import AnomalyDetector, sanitize_point
from model.feature_engineering import (
    compute_features,
    normalize,
    normalize_features,
)
from model.uncertainty import estimate_confidence

# Lazy-loaded ML model
_ml_model = None
_anomaly_detector = AnomalyDetector()


# ── Public interface ───────────────────────────────────────────────────────

def predict_risk(
    point: dict[str, Any],
    history: list[dict[str, Any]] | None = None,
    upstream_data: dict[str, Any] | None = None,
    population_data: dict[str, Any] | None = None,
    model_mode: str | None = None,
) -> dict:
    """Produce a full risk-intelligence prediction for a single location.

    Parameters
    ----------
    point : dict
        Current sensor observation (must contain at least ``rainfall_mm_hr``,
        ``river_level_m``, ``slope_deg``, ``soil_saturation``).
    history : list[dict] | None
        Previous observations (oldest first).
    upstream_data : dict | None
        Upstream sensor data.
    population_data : dict | None
        Population/vulnerability data for the location.
    model_mode : str | None
        Override for ``config.MODEL_MODE``.

    Returns
    -------
    dict
        Full prediction with hazard, exposure, vulnerability, risk, confidence,
        top_factors, explanation, and recommended_action.
    """
    mode = model_mode or config.MODEL_MODE

    # -- 1. Validate & sanitize -------------------------------------------
    quality_report = _anomaly_detector.validate(point, history)
    clean = sanitize_point(point)

    # -- 2. Build time-series for feature engineering ----------------------
    ts = list(history) if history else []
    ts.append(clean)

    # -- 3. Compute features -----------------------------------------------
    features = compute_features(ts, upstream_data)
    norm_features = normalize_features(features)

    # -- 4. Hazard score ---------------------------------------------------
    tree_preds: list[float] | None = None
    if mode == "ml":
        hazard, tree_preds = _predict_hazard_ml(norm_features)
        if hazard is None:
            # Fallback to baseline if ML fails
            hazard = _predict_hazard_baseline(norm_features)
    else:
        hazard = _predict_hazard_baseline(norm_features)

    # -- 5. Exposure & vulnerability ----------------------------------------
    exposure = _compute_exposure(population_data)
    vulnerability = _compute_vulnerability(population_data)

    # -- 6. Combined risk score (geometric-mean-weighted) -------------------
    risk_score = _combine_risk(hazard, exposure, vulnerability)
    label = config.risk_label(risk_score)

    # -- 7. Confidence / uncertainty ----------------------------------------
    conf = estimate_confidence(clean, features, quality_report, tree_preds)

    # -- 8. Top contributing factors ----------------------------------------
    top_factors = _top_factors(norm_features)

    # -- 9. Human-readable explanation --------------------------------------
    explanation = _generate_explanation(top_factors, label, features)

    # -- 10. Recommended action ---------------------------------------------
    trend = _compute_trend(features)
    action, action_reason = _recommended_action(label, conf["confidence"], trend)

    # -- Build output (preserves frontend data contract) --------------------
    result: dict[str, Any] = {}

    # Pass through identity / location fields
    for key in ("id", "name", "lat", "lng"):
        if key in point:
            result[key] = point[key]

    # Raw sensor values
    result["rainfall_mm_hr"] = clean.get("rainfall_mm_hr")
    result["river_level_m"] = clean.get("river_level_m")
    result["slope_deg"] = clean.get("slope_deg")
    result["soil_saturation"] = clean.get("soil_saturation")
    result["historical_incident_density"] = clean.get("historical_incident_density")
    result["population_exposure"] = clean.get("population_exposure")

    # Core risk output
    result["hazard_score"] = round(hazard, 4)
    result["exposure_score"] = round(exposure, 4)
    result["vulnerability_score"] = round(vulnerability, 4)
    result["risk_score"] = round(risk_score, 4)
    result["risk_label"] = label
    result["confidence"] = conf["confidence"]
    result["data_quality_score"] = conf["data_quality_score"]
    result["sensor_status"] = quality_report["sensor_status"]

    # Explanation
    result["top_factors"] = [f["factor"] for f in top_factors[:3]]
    result["top_factors_detail"] = top_factors[:5]
    result["explanation"] = explanation

    # Action
    result["recommended_action"] = action
    result["action_reason"] = action_reason

    # Model metadata
    result["model_mode"] = "ml" if mode == "ml" and tree_preds is not None else "baseline"

    return result


# ── Hazard models ─────────────────────────────────────────────────────────

def _predict_hazard_baseline(norm_features: dict[str, float]) -> float:
    """Explainable weighted-sum hazard model."""
    score = 0.0
    for weight_key, weight_val in config.HAZARD_WEIGHTS.items():
        feature_field = config.HAZARD_FEATURE_MAP.get(weight_key)
        if feature_field:
            score += weight_val * norm_features.get(feature_field, 0.0)
    return max(0.0, min(1.0, score))


def _predict_hazard_ml(
    norm_features: dict[str, float],
) -> tuple[float | None, list[float] | None]:
    """Random Forest hazard prediction with per-tree outputs.

    Returns (hazard_score, per_tree_predictions) or (None, None) on failure.
    """
    global _ml_model
    try:
        if _ml_model is None:
            _ml_model = _load_ml_model()
        if _ml_model is None:
            return None, None

        # Build feature vector in the exact order the model expects
        x = np.array(
            [norm_features.get(f, 0.0) for f in config.ML_FEATURE_NAMES],
            dtype=np.float64,
        ).reshape(1, -1)

        # Replace NaN with 0
        x = np.nan_to_num(x, nan=0.0)

        # Per-tree predictions for uncertainty
        tree_preds = [t.predict(x)[0] for t in _ml_model.estimators_]
        hazard = float(np.mean(tree_preds))
        hazard = max(0.0, min(1.0, hazard))

        return hazard, [float(p) for p in tree_preds]
    except Exception:
        return None, None


def _load_ml_model():
    """Load a serialized Random Forest model if it exists."""
    try:
        import joblib
        path = config.MODEL_SAVE_PATH
        if os.path.exists(path):
            return joblib.load(path)
    except Exception:
        pass
    return None


# ── Exposure & vulnerability ──────────────────────────────────────────────

def _compute_exposure(population_data: dict[str, Any] | None) -> float:
    """Compute exposure score [0, 1] from population data."""
    if not population_data:
        return 0.5  # moderate default

    total = 0.0
    for key in (
        "registered_population", "transient_population", "tourist_population",
        "pilgrim_population", "temporary_workers",
    ):
        val = population_data.get(key, 0)
        try:
            total += float(val)
        except (TypeError, ValueError):
            pass

    # Normalize against reference
    return min(1.0, total / config.MAX_POPULATION_REFERENCE)


def _compute_vulnerability(population_data: dict[str, Any] | None) -> float:
    """Compute vulnerability score [0, 1] from population composition.

    Vulnerability fractions (e.g., elderly_fraction=0.15) are normalized
    against reference maximums and then weighted.  The result is scaled
    so that a community with high proportions of all vulnerable groups
    approaches 1.0.
    """
    if not population_data:
        return 0.5  # moderate default

    total_pop = sum(
        population_data.get(k, 0) for k in (
            "registered_population", "transient_population",
            "tourist_population", "pilgrim_population", "temporary_workers",
        )
    )
    if total_pop <= 0:
        return 0.3

    # Reference maximums for normalization — what counts as 'very high'
    _VULN_REFS: dict[str, float] = {
        "elderly_fraction": 0.25,
        "children_fraction": 0.30,
        "hospital_population": 0.10,
        "mobility_limited_fraction": 0.15,
        "tourist_transient_fraction": 0.40,
    }

    score = 0.0
    for key, weight in config.VULNERABILITY_WEIGHTS.items():
        val = population_data.get(key, 0.0)
        try:
            val = float(val)
        except (TypeError, ValueError):
            val = 0.0
        ref = _VULN_REFS.get(key, 0.3)
        normalized = min(1.0, val / ref) if ref > 0 else 0.0
        score += weight * normalized

    return max(0.0, min(1.0, score))


# ── Risk combination ─────────────────────────────────────────────────────

def _combine_risk(hazard: float, exposure: float, vulnerability: float) -> float:
    """Geometric-mean-weighted risk combination.

    risk = hazard^w_h × exposure^w_e × vulnerability^w_v
    """
    # Clamp to small positive to avoid log(0)
    h = max(0.001, hazard)
    e = max(0.001, exposure)
    v = max(0.001, vulnerability)

    risk = (
        h ** config.RISK_WEIGHT_HAZARD
        * e ** config.RISK_WEIGHT_EXPOSURE
        * v ** config.RISK_WEIGHT_VULNERABILITY
    )
    return max(0.0, min(1.0, risk))


# ── Factor analysis ──────────────────────────────────────────────────────

def _top_factors(norm_features: dict[str, float]) -> list[dict]:
    """Return contributing factors sorted by contribution (descending)."""
    contributions = []
    for weight_key, weight_val in config.HAZARD_WEIGHTS.items():
        feature_field = config.HAZARD_FEATURE_MAP.get(weight_key)
        if feature_field:
            feat_val = norm_features.get(feature_field, 0.0)
            contributions.append({
                "factor": weight_key,
                "feature_field": feature_field,
                "normalized_value": round(feat_val, 4),
                "weight": weight_val,
                "contribution": round(weight_val * feat_val, 4),
            })
    contributions.sort(key=lambda c: c["contribution"], reverse=True)
    return contributions


# ── Explanation generation ────────────────────────────────────────────────

_FACTOR_PHRASES: dict[str, str] = {
    "rainfall_intensity": "high rainfall intensity",
    "rainfall_accumulation": "significant rainfall accumulation",
    "river_level": "elevated river level",
    "river_rise_rate": "rapidly rising river level",
    "slope": "steep terrain",
    "soil_saturation": "high soil saturation",
    "upstream_conditions": "concerning upstream conditions",
    "historical_incident": "historically flood-prone area",
    "other_local_signals": "rapid rainfall increase",
}


def _generate_explanation(
    top_factors: list[dict],
    risk_label: str,
    features: dict[str, float | None],
) -> str:
    """Generate a human-readable explanation from top contributing factors."""
    if not top_factors:
        return "Insufficient data to generate explanation."

    # Pick top 3 non-trivial factors
    significant = [f for f in top_factors if f["contribution"] > 0.01][:3]
    if not significant:
        return f"Risk is {risk_label}. No single dominant factor identified."

    phrases = [_FACTOR_PHRASES.get(f["factor"], f["factor"]) for f in significant]

    if len(phrases) == 1:
        reason_str = phrases[0]
    elif len(phrases) == 2:
        reason_str = f"{phrases[0]} and {phrases[1]}"
    else:
        reason_str = f"{phrases[0]}, {phrases[1]}, and {phrases[2]}"

    return f"Risk is {risk_label.lower()} driven mainly by {reason_str}."


# ── Trend & action ────────────────────────────────────────────────────────

def _compute_trend(features: dict[str, float | None]) -> str:
    """Determine whether conditions are 'increasing', 'stable', or 'decreasing'."""
    indicators = []
    for field in ("rainfall_change_30min", "river_rise_rate", "soil_saturation_change"):
        val = features.get(field)
        if val is not None:
            indicators.append(val)
    if not indicators:
        return "unknown"
    avg = sum(indicators) / len(indicators)
    if avg > 0.05:
        return "increasing"
    elif avg < -0.05:
        return "decreasing"
    return "stable"


def _recommended_action(
    risk_label: str,
    confidence: float,
    trend: str,
) -> tuple[str, str]:
    """Apply alert policy to determine recommended action.

    Returns (action, reason).
    """
    for rule in config.ALERT_POLICY:
        if rule["risk_label"] != risk_label:
            continue
        if "min_confidence" in rule and confidence < rule["min_confidence"]:
            continue
        if "trend" in rule and trend != rule["trend"]:
            continue
        action = rule["action"]
        reason = _action_reason(risk_label, action, confidence, trend)
        return action, reason

    # Default fallback
    return "MONITOR", f"Risk is {risk_label.lower()} with no escalation triggers."


def _action_reason(risk_label: str, action: str, confidence: float, trend: str) -> str:
    """Generate a human-readable reason for the recommended action."""
    parts = [f"Risk is {risk_label.lower()}"]
    if trend == "increasing":
        parts.append("conditions are rapidly worsening")
    if confidence >= 0.7:
        parts.append("prediction confidence is high")
    elif confidence < 0.5:
        parts.append("but prediction confidence is low")
    return "; ".join(parts) + "."
