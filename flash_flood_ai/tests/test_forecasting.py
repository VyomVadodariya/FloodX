"""
test_forecasting.py — Unit Tests for Feature Engineering & Forecasting
=======================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from model.feature_engineering import (
    compute_features,
    normalize,
    normalize_features,
)
from model.forecasting_model import forecast_risk


# ── Feature engineering tests ─────────────────────────────────────────────

class TestFeatureEngineering:

    def _sample_ts(self) -> list[dict]:
        return [
            {"rainfall_mm_hr": 10, "river_level_m": 1.0, "soil_saturation": 0.3,
             "slope_deg": 20, "historical_incident_density": 3.0, "population_exposure": 1.0},
            {"rainfall_mm_hr": 15, "river_level_m": 1.2, "soil_saturation": 0.35,
             "slope_deg": 20, "historical_incident_density": 3.0, "population_exposure": 1.0},
            {"rainfall_mm_hr": 22, "river_level_m": 1.5, "soil_saturation": 0.42,
             "slope_deg": 20, "historical_incident_density": 3.0, "population_exposure": 1.0},
        ]

    def test_basic_features_computed(self):
        features = compute_features(self._sample_ts())
        assert features["rainfall_mm_hr"] == 22
        assert features["river_level_m"] == 1.5
        assert features["slope_deg"] == 20

    def test_rainfall_change_computed(self):
        features = compute_features(self._sample_ts())
        assert features["rainfall_change_15min"] is not None
        assert features["rainfall_change_15min"] == pytest.approx(22 - 15, abs=0.01)

    def test_river_rise_rate_computed(self):
        features = compute_features(self._sample_ts())
        assert features["river_rise_rate"] is not None
        assert features["river_rise_rate"] == pytest.approx(1.5 - 1.2, abs=0.01)

    def test_rolling_mean_correct(self):
        features = compute_features(self._sample_ts())
        # Mean of last 2: (15 + 22) / 2 = 18.5
        assert features["rainfall_30min"] == pytest.approx(18.5, abs=0.01)

    def test_accumulation_computed(self):
        features = compute_features(self._sample_ts())
        # Sum of all 3 values × 0.25 (15-min fraction of hour)
        expected = (10 + 15 + 22) * 0.25
        assert features["rainfall_accumulation_1hr"] == pytest.approx(expected, abs=0.01)

    def test_empty_timeseries(self):
        features = compute_features([])
        assert all(v is None for v in features.values())

    def test_single_observation(self):
        ts = [{"rainfall_mm_hr": 20, "river_level_m": 1.0, "soil_saturation": 0.4}]
        features = compute_features(ts)
        assert features["rainfall_mm_hr"] == 20
        assert features["rainfall_change_15min"] is None  # no previous obs

    def test_upstream_data_integration(self):
        upstream = {
            "upstream_rainfall": 50.0,
            "upstream_river_level": 3.0,
            "upstream_river_rise_rate": 0.5,
        }
        features = compute_features(self._sample_ts(), upstream_data=upstream)
        assert features["upstream_rainfall"] == 50.0
        assert features["upstream_river_level"] == 3.0

    def test_upstream_fallback(self):
        features = compute_features(self._sample_ts(), upstream_data=None)
        assert features["upstream_rainfall"] is None

    def test_normalize_basic(self):
        assert normalize(50.0, "rainfall_mm_hr") == pytest.approx(0.5, abs=0.01)
        assert normalize(0.0, "rainfall_mm_hr") == 0.0
        assert normalize(100.0, "rainfall_mm_hr") == 1.0

    def test_normalize_clamps(self):
        assert normalize(200.0, "rainfall_mm_hr") == 1.0
        assert normalize(-10.0, "rainfall_mm_hr") == 0.0

    def test_normalize_none(self):
        assert normalize(None, "rainfall_mm_hr") == 0.0


# ── Forecasting tests ────────────────────────────────────────────────────

class TestForecasting:

    def _escalating_ts(self) -> list[dict]:
        return [
            {"rainfall_mm_hr": 10, "river_level_m": 0.8, "slope_deg": 25,
             "soil_saturation": 0.3, "historical_incident_density": 4.0,
             "population_exposure": 1.0},
            {"rainfall_mm_hr": 20, "river_level_m": 1.2, "slope_deg": 25,
             "soil_saturation": 0.38, "historical_incident_density": 4.0,
             "population_exposure": 1.0},
            {"rainfall_mm_hr": 32, "river_level_m": 1.7, "slope_deg": 25,
             "soil_saturation": 0.48, "historical_incident_density": 4.0,
             "population_exposure": 1.0},
        ]

    def test_forecast_returns_all_horizons(self):
        result = forecast_risk(self._escalating_ts())
        assert "15_min" in result["forecast"]
        assert "30_min" in result["forecast"]
        assert "60_min" in result["forecast"]
        assert "120_min" in result["forecast"]

    def test_forecast_values_in_range(self):
        result = forecast_risk(self._escalating_ts())
        for key, val in result["forecast"].items():
            if val is not None:
                assert 0 <= val <= 1, f"Forecast {key}={val} out of range"

    def test_escalating_forecast_trend(self):
        result = forecast_risk(self._escalating_ts())
        # With escalating inputs, later horizons should generally be >= earlier
        vals = [result["forecast"][f"{h}_min"] for h in [15, 30, 60, 120]]
        valid = [v for v in vals if v is not None]
        # At least the trend should be non-decreasing for escalating input
        if len(valid) >= 2:
            assert valid[-1] >= valid[0] - 0.05  # allow small tolerance

    def test_current_risk_present(self):
        result = forecast_risk(self._escalating_ts())
        assert result["current_risk"] is not None

    def test_time_to_danger_type(self):
        result = forecast_risk(self._escalating_ts())
        t2c = result["estimated_time_to_critical_min"]
        assert t2c is None or isinstance(t2c, int)

    def test_insufficient_data(self):
        result = forecast_risk([])
        assert result["method"] == "insufficient_data"
        assert result["current_risk"] is None

    def test_single_point_insufficient(self):
        result = forecast_risk([{"rainfall_mm_hr": 10, "river_level_m": 1.0}])
        assert result["method"] == "insufficient_data"

    def test_custom_horizons(self):
        result = forecast_risk(self._escalating_ts(), horizons=[10, 45])
        assert "10_min" in result["forecast"]
        assert "45_min" in result["forecast"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
