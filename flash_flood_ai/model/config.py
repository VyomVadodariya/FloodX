"""
config.py — Centralized Configuration for Flash Flood AI System
================================================================

All thresholds, weights, feature definitions, model parameters, and routing
penalties live here.  Nothing is scattered as magic numbers in other modules.

Region-specific overrides can be applied by replacing or layering on top of
these defaults.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------
RANDOM_SEED: int = 42

# Model mode: "baseline" (explainable weighted) or "ml" (Random Forest)
MODEL_MODE: str = "baseline"

# ---------------------------------------------------------------------------
# Physically-sensible normalization bounds  (region-configurable)
# Each tuple is (min_safe, max_critical).  Values are clipped then linearly
# mapped to [0, 1].
# ---------------------------------------------------------------------------
NORMALIZATION_BOUNDS: dict[str, tuple[float, float]] = {
    "rainfall_mm_hr":               (0.0, 100.0),
    "rainfall_accumulation_1hr":    (0.0, 150.0),
    "rainfall_accumulation_3hr":    (0.0, 300.0),
    "rainfall_accumulation_6hr":    (0.0, 500.0),
    "river_level_m":                (0.0, 5.0),
    "river_rise_rate":              (0.0, 1.0),     # m per 15 min
    "slope_deg":                    (0.0, 45.0),
    "soil_saturation":              (0.0, 1.0),
    "historical_incident_density":  (0.0, 10.0),
    "population_exposure":          (0.0, 5.0),
    "upstream_rainfall":            (0.0, 100.0),
    "upstream_river_level":         (0.0, 5.0),
    "upstream_river_rise_rate":     (0.0, 1.0),
    "rainfall_change_30min":        (-20.0, 50.0),
    "river_level_change_30min":     (-0.5, 2.0),
    "rainfall_acceleration":        (-10.0, 30.0),
    "river_rise_acceleration":      (-0.3, 1.0),
    "soil_saturation_change":       (-0.1, 0.3),
}

# ---------------------------------------------------------------------------
# Hazard model weights  (Explainable baseline — must sum to 1.0)
# ---------------------------------------------------------------------------
HAZARD_WEIGHTS: dict[str, float] = {
    "rainfall_intensity":       0.25,
    "rainfall_accumulation":    0.10,
    "river_level":              0.20,
    "river_rise_rate":          0.10,
    "slope":                    0.10,
    "soil_saturation":          0.10,
    "upstream_conditions":      0.05,
    "historical_incident":      0.05,
    "other_local_signals":      0.05,
}

# Mapping from hazard-weight keys → actual data-field names
HAZARD_FEATURE_MAP: dict[str, str] = {
    "rainfall_intensity":       "rainfall_mm_hr",
    "rainfall_accumulation":    "rainfall_accumulation_1hr",
    "river_level":              "river_level_m",
    "river_rise_rate":          "river_rise_rate",
    "slope":                    "slope_deg",
    "soil_saturation":          "soil_saturation",
    "upstream_conditions":      "upstream_rainfall",
    "historical_incident":      "historical_incident_density",
    "other_local_signals":      "rainfall_change_30min",
}

# ---------------------------------------------------------------------------
# Risk combination weights  (geometric-mean exponents, must sum to 1.0)
# ---------------------------------------------------------------------------
RISK_WEIGHT_HAZARD: float = 0.60
RISK_WEIGHT_EXPOSURE: float = 0.25
RISK_WEIGHT_VULNERABILITY: float = 0.15

# ---------------------------------------------------------------------------
# Risk-label thresholds
# ---------------------------------------------------------------------------
RISK_THRESHOLDS: dict[str, tuple[float, float]] = {
    "LOW":      (0.00, 0.29),
    "MODERATE": (0.30, 0.54),
    "HIGH":     (0.55, 0.74),
    "CRITICAL": (0.75, 1.00),
}

def risk_label(score: float) -> str:
    """Return the risk label for a given score."""
    for label, (lo, hi) in RISK_THRESHOLDS.items():
        if lo <= score <= hi:
            return label
    return "CRITICAL" if score > 1.0 else "LOW"

# ---------------------------------------------------------------------------
# Forecast horizons (minutes)
# ---------------------------------------------------------------------------
FORECAST_HORIZONS: list[int] = [15, 30, 60, 120]

# ---------------------------------------------------------------------------
# Sensor anomaly thresholds
# ---------------------------------------------------------------------------
SENSOR_VALID_RANGES: dict[str, tuple[float, float]] = {
    "rainfall_mm_hr":       (0.0, 500.0),
    "river_level_m":        (0.0, 30.0),
    "slope_deg":            (0.0, 90.0),
    "soil_saturation":      (0.0, 1.0),
    "historical_incident_density": (0.0, 100.0),
    "population_exposure":  (0.0, 100.0),
}

# Maximum plausible jump per 15-minute interval
SENSOR_MAX_JUMP: dict[str, float] = {
    "rainfall_mm_hr":   80.0,
    "river_level_m":    2.0,
    "soil_saturation":  0.3,
}

# Staleness: if identical readings repeat this many times, flag
SENSOR_STALE_REPEAT_LIMIT: int = 6

# ---------------------------------------------------------------------------
# Confidence / uncertainty weights
# ---------------------------------------------------------------------------
CONFIDENCE_WEIGHTS: dict[str, float] = {
    "data_quality":         0.20,
    "sensor_reliability":   0.15,
    "feature_completeness": 0.20,
    "model_uncertainty":    0.25,
    "signal_agreement":     0.20,
}

# ---------------------------------------------------------------------------
# Evacuation routing
# ---------------------------------------------------------------------------
ROUTING_RISK_PENALTY_ALPHA: float = 50.0       # current-risk weight
ROUTING_PREDICTED_RISK_PENALTY_BETA: float = 80.0  # predicted-risk weight
CRITICAL_ROAD_RISK_THRESHOLD: float = 0.80     # block edge above this

# ---------------------------------------------------------------------------
# Alert-policy decision matrix
# ---------------------------------------------------------------------------
ALERT_POLICY: list[dict] = [
    {"risk_label": "CRITICAL", "min_confidence": 0.70, "action": "EVACUATE"},
    {"risk_label": "HIGH",     "min_confidence": 0.60, "trend": "increasing", "action": "PREPARE"},
    {"risk_label": "MODERATE", "trend": "increasing", "action": "ALERT"},
    {"risk_label": "MODERATE", "action": "MONITOR"},
    {"risk_label": "LOW",      "action": "MONITOR"},
]

# ---------------------------------------------------------------------------
# Population / vulnerability defaults
# ---------------------------------------------------------------------------
VULNERABILITY_WEIGHTS: dict[str, float] = {
    "elderly_fraction":           0.25,
    "children_fraction":          0.20,
    "hospital_population":        0.20,
    "mobility_limited_fraction":  0.20,
    "tourist_transient_fraction": 0.15,
}

# Max population for exposure normalization
MAX_POPULATION_REFERENCE: float = 10000.0

# ---------------------------------------------------------------------------
# ML model hyper-parameters
# ---------------------------------------------------------------------------
RF_N_ESTIMATORS: int = 100
RF_MAX_DEPTH: int | None = 12
RF_MIN_SAMPLES_LEAF: int = 5

# Feature list used by the ML model (order matters for training)
ML_FEATURE_NAMES: list[str] = [
    "rainfall_mm_hr",
    "rainfall_accumulation_1hr",
    "rainfall_accumulation_3hr",
    "rainfall_change_30min",
    "rainfall_acceleration",
    "river_level_m",
    "river_rise_rate",
    "river_level_change_30min",
    "river_rise_acceleration",
    "slope_deg",
    "soil_saturation",
    "soil_saturation_change",
    "historical_incident_density",
    "upstream_rainfall",
    "upstream_river_level",
    "upstream_river_rise_rate",
]

# Path for serialized model
MODEL_SAVE_PATH: str = "flash_flood_ai/model/trained_model.joblib"
