"""
test_risk_engine.py — Unit Tests for Risk Engine
==================================================
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from model.risk_engine import predict_risk
from model.anomaly_detector import validate_input, AnomalyDetector, sanitize_point


# ── Risk engine tests ─────────────────────────────────────────────────────

class TestPredictRisk:
    """Tests for the predict_risk function."""

    def _low_point(self) -> dict:
        return {
            "id": "test_low", "name": "Test Low",
            "rainfall_mm_hr": 2, "river_level_m": 0.3, "slope_deg": 8,
            "soil_saturation": 0.15, "historical_incident_density": 0.5,
            "population_exposure": 0.2,
        }

    def _critical_point(self) -> dict:
        return {
            "id": "test_critical", "name": "Test Critical",
            "rainfall_mm_hr": 90, "river_level_m": 4.5, "slope_deg": 40,
            "soil_saturation": 0.95, "historical_incident_density": 9.0,
            "population_exposure": 3.0,
        }

    def test_low_risk_returns_low_label(self):
        result = predict_risk(self._low_point())
        assert result["risk_label"] in ("LOW", "MODERATE")
        assert result["risk_score"] < 0.55

    def test_critical_risk_returns_high_or_critical(self):
        result = predict_risk(self._critical_point())
        assert result["risk_label"] in ("HIGH", "CRITICAL")
        assert result["risk_score"] > 0.50

    def test_output_has_required_fields(self):
        result = predict_risk(self._low_point())
        required = [
            "risk_score", "risk_label", "confidence", "hazard_score",
            "exposure_score", "vulnerability_score", "explanation",
            "top_factors", "recommended_action", "sensor_status",
            "data_quality_score", "model_mode",
        ]
        for field in required:
            assert field in result, f"Missing field: {field}"

    def test_risk_score_in_range(self):
        for pt in [self._low_point(), self._critical_point()]:
            result = predict_risk(pt)
            assert 0 <= result["risk_score"] <= 1
            assert 0 <= result["hazard_score"] <= 1
            assert 0 <= result["confidence"] <= 1

    def test_missing_data_does_not_crash(self):
        point = {"id": "empty", "name": "Empty"}
        result = predict_risk(point)
        assert "risk_score" in result
        assert result["sensor_status"] in ("DEGRADED", "CRITICAL")

    def test_nan_values_do_not_crash(self):
        point = {
            "rainfall_mm_hr": float("nan"),
            "river_level_m": None,
            "slope_deg": 20,
            "soil_saturation": float("nan"),
        }
        result = predict_risk(point)
        assert "risk_score" in result

    def test_negative_values_handled(self):
        point = {
            "rainfall_mm_hr": -10,
            "river_level_m": -5,
            "slope_deg": -1,
            "soil_saturation": -0.5,
        }
        result = predict_risk(point)
        assert result["risk_score"] >= 0

    def test_extreme_values_handled(self):
        point = {
            "rainfall_mm_hr": 999,
            "river_level_m": 100,
            "slope_deg": 90,
            "soil_saturation": 5.0,
        }
        result = predict_risk(point)
        assert result["risk_score"] <= 1.0

    def test_with_history(self):
        history = [
            {"rainfall_mm_hr": 10, "river_level_m": 1.0, "slope_deg": 20,
             "soil_saturation": 0.3, "historical_incident_density": 2.0,
             "population_exposure": 0.5},
        ]
        point = {
            "rainfall_mm_hr": 25, "river_level_m": 1.5, "slope_deg": 20,
            "soil_saturation": 0.45, "historical_incident_density": 2.0,
            "population_exposure": 0.5,
        }
        result = predict_risk(point, history=history)
        assert "risk_score" in result

    def test_with_population_data(self):
        pop = {
            "registered_population": 5000,
            "tourist_population": 1000,
            "elderly_fraction": 0.15,
            "children_fraction": 0.20,
        }
        result = predict_risk(self._critical_point(), population_data=pop)
        assert result["exposure_score"] > 0.3

    def test_baseline_mode(self):
        result = predict_risk(self._low_point(), model_mode="baseline")
        assert result["model_mode"] == "baseline"

    def test_ml_fallback(self):
        """ML mode falls back to baseline when no trained model exists."""
        result = predict_risk(self._low_point(), model_mode="ml")
        assert result["model_mode"] == "baseline"  # no model file → fallback


# ── Anomaly detector tests ────────────────────────────────────────────────

class TestAnomalyDetector:

    def test_clean_data_returns_ok(self):
        point = {
            "rainfall_mm_hr": 20, "river_level_m": 1.5, "slope_deg": 25,
            "soil_saturation": 0.5, "historical_incident_density": 3.0,
            "population_exposure": 1.0,
        }
        result = validate_input(point)
        assert result["sensor_status"] == "OK"
        assert result["data_quality_score"] > 0.8

    def test_missing_fields_detected(self):
        result = validate_input({"slope_deg": 20})
        assert len(result["missing_fields"]) > 0
        assert "rainfall_mm_hr" in result["missing_fields"]

    def test_negative_rainfall_detected(self):
        point = {"rainfall_mm_hr": -5, "river_level_m": 1.0, "slope_deg": 20,
                 "soil_saturation": 0.5}
        result = validate_input(point)
        assert any("below_min" in a for a in result["anomalies"])

    def test_impossible_saturation_detected(self):
        point = {"rainfall_mm_hr": 10, "river_level_m": 1.0, "slope_deg": 20,
                 "soil_saturation": 1.5}
        result = validate_input(point)
        assert any("above_max" in a for a in result["anomalies"])

    def test_sensor_jump_detected(self):
        detector = AnomalyDetector()
        history = [{"rainfall_mm_hr": 10, "river_level_m": 1.0}]
        point = {"rainfall_mm_hr": 100, "river_level_m": 1.0}  # jump of 90
        result = detector.validate(point, history)
        assert any("sensor_jump" in a for a in result["anomalies"])

    def test_sanitize_clamps_values(self):
        point = {"rainfall_mm_hr": -10, "soil_saturation": 2.0}
        clean = sanitize_point(point)
        assert clean["rainfall_mm_hr"] == 0.0
        assert clean["soil_saturation"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
