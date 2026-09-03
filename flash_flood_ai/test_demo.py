"""
test_demo.py — End-to-End System Demonstration
==============================================

Simulates a complete flash flood event, running data through the fully
integrated pipeline: Risk Engine -> Dynamic Routing -> GenAI Alerts.
"""

import os
import json
import time
from backend.lambda_alert_handler import lambda_handler

# Ensure we are in mock mode for the demo
os.environ["MONGODB_URI"] = ""

def run_demo():
    print("==========================================================")
    print("FLOODX: AI FLASH-FLOOD INTELLIGENCE & EVACUATION SYSTEM")
    print("==========================================================\n")
    
    print("[SYSTEM] Initializing models and backend adapters (Mock Mode)...\n")
    
    # Simulate a Cloudburst hitting Midvalley 02
    base_payload = {
        "id": "midvalley_02",
        "name": "Bridge Market Colony",
        "lat": 33.36,
        "lng": 75.71,
        "zone": "midvalley",
        "slope_deg": 18,
        "altitude_m": 2200,
        "historical_incident_density": 6.1,
        "population_exposure": 0.95,
        "registered_population": 4500,
        "tourist_population": 1500,
        "elderly_fraction": 0.25,
        "children_fraction": 0.35
    }

    scenarios = [
        {
            "desc": "T=0: Normal Weather",
            "telemetry": {"rainfall_mm_hr": 2.0, "river_level_m": 0.5, "soil_saturation": 0.25}
        },
        {
            "desc": "T=+30m: Heavy Rain Starts",
            "telemetry": {"rainfall_mm_hr": 35.0, "river_level_m": 1.2, "soil_saturation": 0.45}
        },
        {
            "desc": "T=+60m: Cloudburst / Rapid River Rise",
            "telemetry": {"rainfall_mm_hr": 140.0, "river_level_m": 8.5, "soil_saturation": 0.99, "upstream_rainfall": 80.0, "upstream_river_rise_rate": 2.5}
        }
    ]

    for i, step in enumerate(scenarios):
        print(f"==========================================================")
        print(f"STEP: {step['desc']}")
        print(f"==========================================================")
        
        payload = {**base_payload, **step["telemetry"]}
        print(f"[INPUT] Sensor Payload received for {payload['name']}")
        print(f"        Rain: {payload['rainfall_mm_hr']} mm/hr | River: {payload['river_level_m']} m | Soil: {payload['soil_saturation']}")
        
        # Invoke the Orchestrator Lambda
        response = lambda_handler(payload, context=None)
        
        if response["statusCode"] != 200:
            print(f"[ERROR] Pipeline failed: {response}")
            continue
            
        data = json.loads(response["body"])
        risk = data.get("risk_assessment", {})
        routing = data.get("evacuation_routing")
        alert = data.get("emergency_alert")
        
        print("\n[AI RISK ENGINE]")
        print(f"  Risk Score:  {risk.get('risk_score')}")
        print(f"  Risk Label:  {risk.get('risk_label')}")
        print(f"  Confidence:  {risk.get('confidence')} (Data Quality: {risk.get('data_quality_score')})")
        print(f"  Explanation: {risk.get('explanation')}")
        
        if risk.get('risk_change'):
            change = risk['risk_change']
            print(f"  Change:      {change} (from {risk.get('previous_score')})")
            
        if routing:
            print("\n[DYNAMIC ROUTING ENGINE]")
            print(f"  Status: {routing.get('status')}")
            if routing.get('status') == 'success':
                print(f"  Route:  {' -> '.join(routing.get('route', []))}")
                print(f"  Time:   {routing.get('travel_time')} mins")
            else:
                print(f"  Alert:  {routing.get('message')}")
                
        if alert:
            print("\n[GenAI EMERGENCY ALERT]")
            print(f"  Title:   {alert.get('alert_title')}")
            print(f"  Action:  {alert.get('recommended_action')}")
            print(f"  Public:  {alert.get('civilian_message')}")
            
        print("\n")
        time.sleep(1)


if __name__ == "__main__":
    run_demo()
