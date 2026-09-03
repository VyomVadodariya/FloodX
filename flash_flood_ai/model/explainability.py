"""
explainability.py — Explanation, Change Analysis & Counterfactual
==================================================================

Every prediction includes:
- Human-readable explanation of top contributing factors
- Change explanation (current vs previous risk)
- Counterfactual: what would need to change for risk to decrease

For ML models, uses feature importance.  SHAP is not included to avoid
unnecessary dependency — the interface supports it if added later.
"""

from __future__ import annotations

from typing import Any

from model import config
from model.feature_engineering import normalize


# ── Factor descriptions for human-readable output ─────────────────────────

_FACTOR_DESCRIPTIONS: dict[str, str] = {
    "rainfall_mm_hr":               "rainfall intensity",
    "rainfall_accumulation_1hr":    "rainfall accumulation (1hr)",
    "rainfall_accumulation_3hr":    "rainfall accumulation (3hr)",
    "rainfall_change_30min":        "rainfall rate of change (30min)",
    "rainfall_acceleration":        "rainfall acceleration",
    "river_level_m":                "river level",
    "river_rise_rate":              "river rise rate",
    "river_level_change_30min":     "river level change (30min)",
    "river_rise_acceleration":      "river rise acceleration",
    "slope_deg":                    "terrain slope",
    "soil_saturation":              "soil saturation",
    "soil_saturation_change":       "soil saturation change",
    "historical_incident_density":  "historical flood incident density",
    "upstream_rainfall":            "upstream rainfall",
    "upstream_river_level":         "upstream river level",
    "upstream_river_rise_rate":     "upstream river rise rate",
    "population_exposure":          "population exposure",
}


# ── Public interface ───────────────────────────────────────────────────────

def explain_prediction(
    current: dict[str, Any],
    previous: dict[str, Any] | None = None,
) -> dict:
    """Generate full explanation for a risk prediction.

    Parameters
    ----------
    current : dict
        Output from ``predict_risk()`` (must include ``top_factors_detail``,
        ``risk_score``, ``risk_label``).
    previous : dict | None
        Previous ``predict_risk()`` output for change explanation.

    Returns
    -------
    dict
        ``explanation``       – human-readable summary
        ``top_factors``       – list of {factor, contribution}
        ``change``            – change analysis dict (if *previous* given)
        ``change_explanation`` – human-readable change summary
    """
    result: dict[str, Any] = {}

    # Top factors
    top = current.get("top_factors_detail", [])
    result["top_factors"] = [
        {"factor": f["factor"], "contribution": f["contribution"]}
        for f in top
    ]
    result["explanation"] = current.get("explanation", "")

    # Change analysis
    if previous:
        change = _compute_change(current, previous)
        result["change"] = change
        result["change_explanation"] = _change_explanation(change, current, previous)
    else:
        result["change"] = None
        result["change_explanation"] = None

    return result


def generate_counterfactual(
    features: dict[str, float | None],
    current_risk: float,
    target_label: str = "MODERATE",
) -> dict:
    """Determine what feature changes would reduce risk below *target_label*.

    Parameters
    ----------
    features : dict
        Current engineered features (raw, not normalized).
    current_risk : float
        Current risk score.
    target_label : str
        Target risk label to drop below (default "MODERATE", i.e. < 0.30).

    Returns
    -------
    dict
        ``target_label``    – the target
        ``target_threshold``– the score to drop below
        ``suggestions``     – list of {field, current, required, description}
        ``disclaimer``      – caveat about model-derived scenarios
    """
    # Find upper bound of the target label
    target_threshold = config.RISK_THRESHOLDS.get(target_label, (0, 0.54))[1]

    if current_risk <= target_threshold:
        return {
            "target_label": target_label,
            "target_threshold": target_threshold,
            "suggestions": [],
            "note": f"Risk is already at or below {target_label}.",
            "disclaimer": "",
        }

    suggestions = []

    # For each major hazard input, estimate what value would be needed
    for weight_key, feature_field in config.HAZARD_FEATURE_MAP.items():
        raw_val = features.get(feature_field)
        if raw_val is None:
            continue

        bounds = config.NORMALIZATION_BOUNDS.get(feature_field)
        if not bounds:
            continue
        lo, hi = bounds

        # How much would risk decrease if this feature were reduced to its safe value?
        weight = config.HAZARD_WEIGHTS.get(weight_key, 0)
        if weight < 0.05:
            continue  # skip minor factors

        norm_val = normalize(raw_val, feature_field)
        if norm_val < 0.3:
            continue  # already low

        # Estimate the threshold: if this factor were reduced to norm_target,
        # hazard would decrease by weight * (norm_val - norm_target)
        required_reduction = (current_risk - target_threshold)
        norm_target = max(0, norm_val - required_reduction / weight)
        required_val = lo + norm_target * (hi - lo)

        desc = _FACTOR_DESCRIPTIONS.get(feature_field, feature_field)
        unit = _get_unit(feature_field)

        suggestions.append({
            "field": feature_field,
            "description": desc,
            "current_value": round(raw_val, 2),
            "required_value": round(required_val, 2),
            "unit": unit,
            "narrative": (
                f"Risk would likely fall below {target_label} if {desc} "
                f"drops below approximately {required_val:.1f}{unit}, "
                f"assuming other conditions remain similar."
            ),
        })

    # Sort by how close the required value is to safe range
    suggestions.sort(key=lambda s: abs(s["current_value"] - s["required_value"]))

    return {
        "target_label": target_label,
        "target_threshold": target_threshold,
        "suggestions": suggestions[:3],
        "disclaimer": (
            "These are model-derived scenarios, not guarantees. "
            "Actual conditions may differ."
        ),
    }


# ── Internal helpers ──────────────────────────────────────────────────────

def _compute_change(current: dict, previous: dict) -> dict:
    """Compute risk change between two predictions."""
    cur_risk = current.get("risk_score", 0)
    prev_risk = previous.get("risk_score", 0)
    delta = cur_risk - prev_risk

    return {
        "previous_risk": round(prev_risk, 4),
        "current_risk": round(cur_risk, 4),
        "previous_label": previous.get("risk_label", "UNKNOWN"),
        "current_label": current.get("risk_label", "UNKNOWN"),
        "delta": round(delta, 4),
        "direction": "increased" if delta > 0.01 else ("decreased" if delta < -0.01 else "stable"),
    }


def _change_explanation(
    change: dict,
    current: dict,
    previous: dict,
) -> str:
    """Generate human-readable change explanation."""
    direction = change["direction"]
    delta = abs(change["delta"])

    if direction == "stable":
        return (
            f"Risk remained stable at {change['current_label']} "
            f"({change['current_risk']:.2f})."
        )

    # Identify which factors changed most
    cur_factors = {f["factor"]: f for f in current.get("top_factors_detail", [])}
    prev_factors = {f["factor"]: f for f in previous.get("top_factors_detail", [])}

    changes = []
    for factor, cur_f in cur_factors.items():
        prev_f = prev_factors.get(factor)
        if prev_f:
            f_delta = cur_f["contribution"] - prev_f["contribution"]
            if abs(f_delta) > 0.01:
                changes.append((factor, f_delta))

    changes.sort(key=lambda x: abs(x[1]), reverse=True)

    magnitude = "sharply" if delta > 0.2 else ("moderately" if delta > 0.1 else "slightly")

    reason_parts = []
    for factor, f_delta in changes[:2]:
        phrase = _FACTOR_DESCRIPTIONS.get(
            config.HAZARD_FEATURE_MAP.get(factor, ""),
            factor,
        )
        dir_word = "increased" if f_delta > 0 else "decreased"
        reason_parts.append(f"{phrase} {dir_word}")

    if reason_parts:
        reasons = " and ".join(reason_parts)
        return (
            f"Risk {direction} {magnitude} from {change['previous_label']} "
            f"({change['previous_risk']:.2f}) to {change['current_label']} "
            f"({change['current_risk']:.2f}) because {reasons}."
        )

    return (
        f"Risk {direction} {magnitude} from {change['previous_label']} "
        f"({change['previous_risk']:.2f}) to {change['current_label']} "
        f"({change['current_risk']:.2f})."
    )


def _get_unit(field: str) -> str:
    """Return the unit string for a field."""
    units = {
        "rainfall_mm_hr": " mm/hr",
        "river_level_m": " m",
        "slope_deg": "°",
        "soil_saturation": "",
        "historical_incident_density": "",
        "upstream_rainfall": " mm/hr",
    }
    return units.get(field, "")
