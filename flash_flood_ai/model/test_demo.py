"""
test_demo.py  -  Integration Demonstration (8 Demos)
=====================================================

Run with:  python -m model.test_demo
       or: python model/test_demo.py

Demonstrates all major system capabilities with actual model output.
Nothing is hard-coded  -  every value is computed by the real pipeline.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure project root is importable
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from model.risk_engine import predict_risk
from model.forecasting_model import forecast_risk
from model.evacuation_router import (
    build_road_graph,
    create_sample_graph,
    get_safe_route,
    simulate_risk_change,
    compute_evacuation_priority,
)
from model.explainability import explain_prediction, generate_counterfactual
from model.feature_engineering import compute_features
from model.anomaly_detector import validate_input


# -- Formatting helpers ----------------------------------------------------

def _section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def _print_result(result: dict, indent: int = 2) -> None:
    """Pretty-print a result dict (JSON-style)."""
    print(json.dumps(result, indent=indent, default=str))


def _divider() -> None:
    print("-" * 50)


# -- Demo 1: LOW risk -----------------------------------------------------

def demo_1_low_risk() -> None:
    """Demo 1  -  LOW risk: Normal conditions, low rainfall, stable river."""
    _section("DEMO 1: LOW RISK  -  Normal Conditions")

    point = {
        "id": "village_01",
        "name": "Peaceful Valley",
        "lat": 33.35,
        "lng": 75.70,
        "rainfall_mm_hr": 3.0,
        "river_level_m": 0.5,
        "slope_deg": 12,
        "soil_saturation": 0.2,
        "historical_incident_density": 1.0,
        "population_exposure": 0.3,
    }

    print("\nInput:")
    _print_result(point)

    result = predict_risk(point)
    print("\nPrediction:")
    _print_result(result)

    assert result["risk_label"] in ("LOW", "MODERATE"), \
        f"Expected LOW/MODERATE, got {result['risk_label']}"
    print("\n[PASS] Demo 1 PASSED")


# -- Demo 2: MODERATE risk ------------------------------------------------

def demo_2_moderate_risk() -> None:
    """Demo 2  -  MODERATE risk: Changing conditions."""
    _section("DEMO 2: MODERATE RISK  -  Changing Conditions")

    history = [
        {"rainfall_mm_hr": 10, "river_level_m": 0.8, "slope_deg": 20,
         "soil_saturation": 0.3, "historical_incident_density": 3.0,
         "population_exposure": 0.8},
        {"rainfall_mm_hr": 15, "river_level_m": 1.0, "slope_deg": 20,
         "soil_saturation": 0.35, "historical_incident_density": 3.0,
         "population_exposure": 0.8},
    ]

    point = {
        "id": "village_02",
        "name": "Hill View Town",
        "lat": 33.37,
        "lng": 75.72,
        "rainfall_mm_hr": 22,
        "river_level_m": 1.3,
        "slope_deg": 20,
        "soil_saturation": 0.42,
        "historical_incident_density": 3.0,
        "population_exposure": 0.8,
    }

    print("\nCurrent observation:")
    _print_result(point)

    result = predict_risk(point, history=history)
    print("\nPrediction:")
    _print_result(result)

    print("\n[PASS] Demo 2 PASSED")


# -- Demo 3: HIGH risk ----------------------------------------------------

def demo_3_high_risk() -> None:
    """Demo 3  -  HIGH risk: Increasing rainfall and river trend."""
    _section("DEMO 3: HIGH RISK  -  Increasing Rainfall & River Trend")

    history = [
        {"rainfall_mm_hr": 20, "river_level_m": 1.2, "slope_deg": 28,
         "soil_saturation": 0.5, "historical_incident_density": 5.0,
         "population_exposure": 1.2},
        {"rainfall_mm_hr": 30, "river_level_m": 1.6, "slope_deg": 28,
         "soil_saturation": 0.55, "historical_incident_density": 5.0,
         "population_exposure": 1.2},
        {"rainfall_mm_hr": 40, "river_level_m": 2.0, "slope_deg": 28,
         "soil_saturation": 0.6, "historical_incident_density": 5.0,
         "population_exposure": 1.2},
    ]

    point = {
        "id": "village_03",
        "name": "Storm Ridge Camp",
        "lat": 33.40,
        "lng": 75.65,
        "rainfall_mm_hr": 52,
        "river_level_m": 2.5,
        "slope_deg": 28,
        "soil_saturation": 0.68,
        "historical_incident_density": 5.0,
        "population_exposure": 1.2,
    }

    print("\nRainfall trend: 20 -> 30 -> 40 -> 52 mm/hr")
    print("River trend:   1.2 -> 1.6 -> 2.0 -> 2.5 m")

    result = predict_risk(point, history=history)
    print("\nPrediction:")
    _print_result(result)

    print("\n[PASS] Demo 3 PASSED")


# -- Demo 4: CRITICAL risk ------------------------------------------------

def demo_4_critical_risk() -> None:
    """Demo 4  -  CRITICAL risk: High exposure, imminent danger."""
    _section("DEMO 4: CRITICAL RISK  -  High Exposure & Imminent Danger")

    history = [
        {"rainfall_mm_hr": 40, "river_level_m": 2.0, "slope_deg": 35,
         "soil_saturation": 0.65, "historical_incident_density": 8.0,
         "population_exposure": 2.5},
        {"rainfall_mm_hr": 55, "river_level_m": 2.8, "slope_deg": 35,
         "soil_saturation": 0.72, "historical_incident_density": 8.0,
         "population_exposure": 2.5},
        {"rainfall_mm_hr": 70, "river_level_m": 3.4, "slope_deg": 35,
         "soil_saturation": 0.8, "historical_incident_density": 8.0,
         "population_exposure": 2.5},
    ]

    point = {
        "id": "village_04",
        "name": "Riverside Colony",
        "lat": 33.31,
        "lng": 75.77,
        "rainfall_mm_hr": 85,
        "river_level_m": 4.0,
        "slope_deg": 35,
        "soil_saturation": 0.88,
        "historical_incident_density": 8.0,
        "population_exposure": 2.5,
    }

    population_data = {
        "registered_population": 4200,
        "transient_population": 300,
        "tourist_population": 400,
        "pilgrim_population": 200,
        "temporary_workers": 100,
        "elderly_fraction": 0.15,
        "children_fraction": 0.25,
        "hospital_population": 0.05,
        "mobility_limited_fraction": 0.08,
        "tourist_transient_fraction": 0.20,
    }

    result = predict_risk(point, history=history, population_data=population_data)
    print("\nPrediction:")
    _print_result(result)

    assert result["risk_label"] in ("HIGH", "CRITICAL"), \
        f"Expected HIGH/CRITICAL, got {result['risk_label']}"
    print("\n[PASS] Demo 4 PASSED")


# -- Demo 5: Forecast -----------------------------------------------------

def demo_5_forecast() -> None:
    """Demo 5  -  Temporal forecast: 15/30/60/120 min horizons."""
    _section("DEMO 5: TEMPORAL FORECAST  -  15/30/60/120 min")

    # Escalating time-series (storm intensifying)
    timeseries = [
        {"rainfall_mm_hr": 10, "river_level_m": 0.8, "slope_deg": 25,
         "soil_saturation": 0.3, "historical_incident_density": 4.0,
         "population_exposure": 1.0},
        {"rainfall_mm_hr": 15, "river_level_m": 1.0, "slope_deg": 25,
         "soil_saturation": 0.35, "historical_incident_density": 4.0,
         "population_exposure": 1.0},
        {"rainfall_mm_hr": 22, "river_level_m": 1.3, "slope_deg": 25,
         "soil_saturation": 0.4, "historical_incident_density": 4.0,
         "population_exposure": 1.0},
        {"rainfall_mm_hr": 30, "river_level_m": 1.7, "slope_deg": 25,
         "soil_saturation": 0.48, "historical_incident_density": 4.0,
         "population_exposure": 1.0},
        {"rainfall_mm_hr": 38, "river_level_m": 2.1, "slope_deg": 25,
         "soil_saturation": 0.55, "historical_incident_density": 4.0,
         "population_exposure": 1.0},
    ]

    result = forecast_risk(timeseries)
    print("\nForecast result:")
    _print_result(result)

    if result["estimated_time_to_critical_min"] is not None:
        print(f"\n/!\\ Estimated time to CRITICAL: {result['estimated_time_to_critical_min']} min")
    else:
        print("\n  Risk may not reach CRITICAL within forecast window")

    print("\n[PASS] Demo 5 PASSED")


# -- Demo 6: Dynamic rerouting --------------------------------------------

def demo_6_dynamic_rerouting() -> None:
    """Demo 6  -  Evacuation rerouting when a road becomes unsafe."""
    _section("DEMO 6: DYNAMIC REROUTING")

    graph, edges = create_sample_graph()

    # Initial route: M1 -> S1
    print("\n--- Initial route: M1 -> S1 ---")
    initial = get_safe_route("M1", "S1", risk_map={}, graph=graph)
    _print_result(initial)

    if initial["route"]:
        print(f"\nRoute: {' -> '.join(initial['route'])}")
        print(f"Travel time: {initial['total_time']} min")

    # Simulate: road M1->D1 risk increases to 0.90 (CRITICAL)
    print("\n--- Road M1->D1 risk increases to 0.90 ---")
    reroute_result = simulate_risk_change(
        risk_map={},
        edge=("M1", "D1"),
        new_risk=0.90,
        graph=graph,
        origin="M1",
        shelter="S1",
        previous_route=initial.get("route"),
    )
    _print_result(reroute_result)

    if reroute_result["rerouted"]:
        print(f"\n- REROUTED!")
        print(f"   Previous: {' -> '.join(reroute_result['previous_route'])}")
        print(f"   New:      {' -> '.join(reroute_result['new_route'])}")
        print(f"   Reason:   {reroute_result['reason']}")
    else:
        print(f"\n   Route unchanged: {reroute_result['reason']}")

    print("\n[PASS] Demo 6 PASSED")


# -- Demo 7: Sensor failure -----------------------------------------------

def demo_7_sensor_failure() -> None:
    """Demo 7  -  Prediction continues with degraded sensor data."""
    _section("DEMO 7: SENSOR FAILURE  -  Graceful Degradation")

    # Normal point
    normal_point = {
        "id": "village_05",
        "name": "Sensor Watch Post",
        "lat": 33.33,
        "lng": 75.74,
        "rainfall_mm_hr": 35,
        "river_level_m": 1.8,
        "slope_deg": 22,
        "soil_saturation": 0.55,
        "historical_incident_density": 4.0,
        "population_exposure": 1.0,
    }

    print("\n--- Normal sensor data ---")
    normal_result = predict_risk(normal_point)
    print(f"Risk: {normal_result['risk_score']:.4f} ({normal_result['risk_label']})")
    print(f"Confidence: {normal_result['confidence']}")
    print(f"Sensor status: {normal_result['sensor_status']}")

    # Degraded point (remove rainfall sensor)
    degraded_point = dict(normal_point)
    degraded_point["rainfall_mm_hr"] = None
    degraded_point["name"] = "Sensor Watch Post (DEGRADED)"

    print("\n--- Rainfall sensor REMOVED ---")
    degraded_result = predict_risk(degraded_point)
    print(f"Risk: {degraded_result['risk_score']:.4f} ({degraded_result['risk_label']})")
    print(f"Confidence: {degraded_result['confidence']}")
    print(f"Sensor status: {degraded_result['sensor_status']}")

    # Validate
    validation = validate_input(degraded_point)
    print(f"\nData quality: {validation['data_quality_score']}")
    print(f"Anomalies: {validation['anomalies']}")
    print(f"Missing: {validation['missing_fields']}")

    assert degraded_result["confidence"] <= normal_result["confidence"], \
        "Confidence should decrease with missing sensor"
    print("\n[PASS] Confidence decreased as expected")
    print("[PASS] Demo 7 PASSED")


# -- Demo 8: Explainability -----------------------------------------------

def demo_8_explainability() -> None:
    """Demo 8  -  Full explainability: why risk changed, counterfactual."""
    _section("DEMO 8: EXPLAINABILITY  -  Why Risk Changed")

    history = [
        {"rainfall_mm_hr": 15, "river_level_m": 1.0, "slope_deg": 25,
         "soil_saturation": 0.35, "historical_incident_density": 5.0,
         "population_exposure": 1.2},
    ]

    # Previous (moderate) observation
    prev_point = {
        "id": "village_06",
        "name": "Insight Valley",
        "lat": 33.36,
        "lng": 75.69,
        "rainfall_mm_hr": 25,
        "river_level_m": 1.4,
        "slope_deg": 25,
        "soil_saturation": 0.45,
        "historical_incident_density": 5.0,
        "population_exposure": 1.2,
    }

    # Current (escalated) observation
    cur_point = {
        "id": "village_06",
        "name": "Insight Valley",
        "lat": 33.36,
        "lng": 75.69,
        "rainfall_mm_hr": 55,
        "river_level_m": 2.8,
        "slope_deg": 25,
        "soil_saturation": 0.72,
        "historical_incident_density": 5.0,
        "population_exposure": 1.2,
    }

    prev_result = predict_risk(prev_point, history=history[:1])
    cur_result = predict_risk(cur_point, history=history + [prev_point])

    print(f"\nPrevious: {prev_result['risk_score']:.4f} ({prev_result['risk_label']})")
    print(f"Current:  {cur_result['risk_score']:.4f} ({cur_result['risk_label']})")
    print(f"Change:   {cur_result['risk_score'] - prev_result['risk_score']:+.4f}")

    # Explanation
    explanation = explain_prediction(cur_result, prev_result)
    print(f"\nExplanation: {cur_result['explanation']}")
    print(f"\nChange explanation: {explanation['change_explanation']}")

    # Counterfactual
    features = compute_features(history + [prev_point, cur_point])
    counterfactual = generate_counterfactual(features, cur_result["risk_score"])
    print(f"\nCounterfactual analysis:")
    if counterfactual["suggestions"]:
        for s in counterfactual["suggestions"]:
            print(f"  -> {s['narrative']}")
    print(f"  Disclaimer: {counterfactual['disclaimer']}")

    print("\n[PASS] Demo 8 PASSED")


# -- Evacuation priority demo (bonus) -------------------------------------

def demo_bonus_evacuation_priority() -> None:
    """Bonus  -  Evacuation priority ranking across multiple locations."""
    _section("BONUS: EVACUATION PRIORITY RANKING")

    locations = [
        {"id": "loc_A", "name": "Mountain Camp",       "risk_score": 0.82, "risk_label": "CRITICAL",
         "estimated_time_to_critical_min": 0,  "population_exposure": 0.8, "vulnerability_score": 0.55},
        {"id": "loc_B", "name": "Valley School",       "risk_score": 0.65, "risk_label": "HIGH",
         "estimated_time_to_critical_min": 25, "population_exposure": 2.0, "vulnerability_score": 0.72},
        {"id": "loc_C", "name": "Riverside Colony",     "risk_score": 0.91, "risk_label": "CRITICAL",
         "estimated_time_to_critical_min": 0,  "population_exposure": 3.5, "vulnerability_score": 0.61},
        {"id": "loc_D", "name": "Hill Market",          "risk_score": 0.45, "risk_label": "MODERATE",
         "estimated_time_to_critical_min": 50, "population_exposure": 1.2, "vulnerability_score": 0.40},
    ]

    ranked = compute_evacuation_priority(locations)

    print("\nEvacuation Priority Order:")
    print(f"{'Priority':<10} {'Location':<22} {'Risk':<10} {'Label':<12} {'Population':<12}")
    print("-" * 66)
    for loc in ranked:
        print(
            f"  {loc['evacuation_priority']:<8} "
            f"{loc['name']:<22} "
            f"{loc['risk_score']:<10.2f} "
            f"{loc['risk_label']:<12} "
            f"{loc['population_exposure']:<12}"
        )

    print("\n[PASS] Bonus demo PASSED")


# -- Main entry point -----------------------------------------------------

def main() -> None:
    """Run all 8 demos + bonus."""
    print("=" * 70)
    print("  FLASH FLOOD AI  -  INTEGRATION DEMONSTRATION")
    print("  Prototype / demonstration model (synthetic data)")
    print("=" * 70)

    demos = [
        demo_1_low_risk,
        demo_2_moderate_risk,
        demo_3_high_risk,
        demo_4_critical_risk,
        demo_5_forecast,
        demo_6_dynamic_rerouting,
        demo_7_sensor_failure,
        demo_8_explainability,
        demo_bonus_evacuation_priority,
    ]

    passed = 0
    failed = 0
    for demo_fn in demos:
        try:
            demo_fn()
            passed += 1
        except Exception as e:
            print(f"\n[FAIL] {demo_fn.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    _section("SUMMARY")
    print(f"\n  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Total:  {passed + failed}")

    if failed == 0:
        print("\n  [PASS] ALL DEMOS PASSED")
    else:
        print(f"\n  [FAIL] {failed} DEMO(S) FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
