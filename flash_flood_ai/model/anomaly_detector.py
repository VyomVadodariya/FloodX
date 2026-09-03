"""
anomaly_detector.py — Sensor Anomaly Detection & Data Validation
=================================================================

Lightweight rule-based anomaly detection for sensor data.  Identifies
impossible values, sudden jumps, stale readings, outliers, and missing
measurements.  Designed with a pluggable interface so an Isolation-Forest
or Autoencoder model can replace the rules later.
"""

from __future__ import annotations

import math
from typing import Any

from model.config import (
    SENSOR_MAX_JUMP,
    SENSOR_STALE_REPEAT_LIMIT,
    SENSOR_VALID_RANGES,
)


# ── Public interface ───────────────────────────────────────────────────────

class AnomalyDetector:
    """Rule-based sensor anomaly detector (pluggable interface).

    Call ``validate(point, history)`` to obtain a structured quality report.
    """

    def validate(
        self,
        point: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
    ) -> dict:
        """Validate a single observation and return a quality report.

        Parameters
        ----------
        point : dict
            Current sensor reading (may contain NaN / None / missing keys).
        history : list[dict] | None
            Previous readings, most-recent last.  Used for jump / stale
            detection.

        Returns
        -------
        dict
            ``sensor_status``  – "OK" | "DEGRADED" | "CRITICAL"
            ``anomalies``      – list of human-readable anomaly descriptions
            ``data_quality_score`` – float in [0, 1]
            ``missing_fields``     – list of expected-but-absent field names
            ``clamped_fields``     – dict of fields that were clamped
        """
        anomalies: list[str] = []
        missing_fields: list[str] = []
        clamped_fields: dict[str, Any] = {}

        # -- 1. Missing / NaN / None ----------------------------------------
        for field in SENSOR_VALID_RANGES:
            val = point.get(field)
            if val is None or (isinstance(val, float) and math.isnan(val)):
                missing_fields.append(field)
                anomalies.append(f"{field}_missing")

        # -- 2. Impossible / out-of-range values ----------------------------
        for field, (lo, hi) in SENSOR_VALID_RANGES.items():
            val = point.get(field)
            if val is None or (isinstance(val, float) and math.isnan(val)):
                continue
            try:
                val = float(val)
            except (TypeError, ValueError):
                anomalies.append(f"{field}_malformed")
                continue
            if val < lo:
                anomalies.append(f"{field}_below_min")
                clamped_fields[field] = lo
            elif val > hi:
                anomalies.append(f"{field}_above_max")
                clamped_fields[field] = hi

        # -- 3. Sudden unrealistic jumps ------------------------------------
        if history:
            prev = history[-1]
            for field, max_jump in SENSOR_MAX_JUMP.items():
                cur = _safe_float(point.get(field))
                prv = _safe_float(prev.get(field))
                if cur is not None and prv is not None:
                    if abs(cur - prv) > max_jump:
                        anomalies.append(f"{field}_sensor_jump")

        # -- 4. Stale / repeated identical readings -------------------------
        if history and len(history) >= SENSOR_STALE_REPEAT_LIMIT:
            tail = history[-SENSOR_STALE_REPEAT_LIMIT:]
            for field in SENSOR_MAX_JUMP:
                vals = [_safe_float(h.get(field)) for h in tail]
                cur = _safe_float(point.get(field))
                if cur is not None and all(v == cur for v in vals if v is not None):
                    anomalies.append(f"{field}_stale_reading")

        # -- 5. Data-quality score ------------------------------------------
        total_checks = max(len(SENSOR_VALID_RANGES) + len(SENSOR_MAX_JUMP), 1)
        penalty = len(anomalies)
        quality = max(0.0, 1.0 - penalty / total_checks)

        # -- 6. Sensor status -----------------------------------------------
        if quality >= 0.85:
            status = "OK"
        elif quality >= 0.50:
            status = "DEGRADED"
        else:
            status = "CRITICAL"

        return {
            "sensor_status": status,
            "anomalies": anomalies,
            "data_quality_score": round(quality, 4),
            "missing_fields": missing_fields,
            "clamped_fields": clamped_fields,
        }


def validate_input(point: dict[str, Any]) -> dict:
    """Module-level convenience — matches the required software interface.

    Parameters
    ----------
    point : dict
        Raw sensor observation.

    Returns
    -------
    dict
        Quality report (see ``AnomalyDetector.validate``).
    """
    return AnomalyDetector().validate(point)


# ── Helpers ────────────────────────────────────────────────────────────────

def _safe_float(val: Any) -> float | None:
    """Return *val* as float, or ``None`` for non-numeric / NaN."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def sanitize_point(point: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *point* with out-of-range values clamped and
    missing numeric fields set to ``None``.

    This ensures downstream code never sees physically-impossible inputs.
    """
    clean: dict[str, Any] = dict(point)
    for field, (lo, hi) in SENSOR_VALID_RANGES.items():
        val = _safe_float(clean.get(field))
        if val is None:
            clean[field] = None
        else:
            clean[field] = max(lo, min(hi, val))
    return clean
