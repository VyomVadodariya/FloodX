"""
FLOODX - FastAPI Integration Server
====================================
Integrates the high-fidelity UI (s:/ideathon) directly with the Python backend ML engine (flash_flood_ai).
"""

import sys
import os

# Add flash_flood_ai directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'flash_flood_ai')))

from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import Python flash_flood_ai modules directly
from model import config, risk_engine, evacuation_router, explainability, uncertainty, anomaly_detector

app = FastAPI(
    title="FLOODX Flash Flood Action-Intelligence API",
    description="Python ML & Hydrological Decision Intelligence Engine API serving FLOODX Command Center UI",
    version="1.0.0"
)

# CORS middleware for dev flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock database of locations matching data.js
LOCATIONS_DB = {
    "loc_riverside": {
        "id": "loc_riverside",
        "name": "Riverside Colony",
        "region": "Mandakini Basin Sector 4",
        "lat": 30.7345,
        "lng": 79.0669,
        "rainfall_mm_hr": 34.5,
        "river_level_m": 4.82,
        "slope_deg": 18.5,
        "soil_saturation": 88,
        "population_exposure": 2400
    },
    "loc_gaurikund": {
        "id": "loc_gaurikund",
        "name": "Gaurikund Market",
        "region": "Mandakini Basin Sector 2",
        "lat": 30.6534,
        "lng": 79.0234,
        "rainfall_mm_hr": 24.2,
        "river_level_m": 3.12,
        "slope_deg": 22.0,
        "soil_saturation": 74,
        "population_exposure": 1850
    },
    "loc_sonprayag": {
        "id": "loc_sonprayag",
        "name": "Sonprayag Junction",
        "region": "Mandakini Basin Sector 1",
        "lat": 30.6312,
        "lng": 79.0112,
        "rainfall_mm_hr": 14.8,
        "river_level_m": 2.45,
        "slope_deg": 14.2,
        "soil_saturation": 62,
        "population_exposure": 3200
    }
}

class RouteRequest(BaseModel):
    origin: str
    destination: str
    road_a_failed: bool = False

@app.get("/api/health")
def get_system_health():
    """Returns AI model status, anomaly detector state, and dataset integrity."""
    return {
        "status": "ONLINE",
        "model_mode": config.MODEL_MODE,
        "hazard_weights": config.HAZARD_WEIGHTS,
        "data_quality_score": 91 if not anomaly_detector.AnomalyDetector().has_warnings() else 72,
        "model_confidence": 77,
        "active_engine": "PRIMARY FLOOD RISK ENGINE (Python flash_flood_ai)"
    }

@app.get("/api/predict/{location_id}")
def predict_location_risk(location_id: str, rain_override: Optional[float] = None):
    """Executes python risk_engine prediction for given location."""
    if location_id not in LOCATIONS_DB:
        loc_data = LOCATIONS_DB["loc_riverside"].copy()
    else:
        loc_data = LOCATIONS_DB[location_id].copy()

    if rain_override is not None:
        loc_data["rainfall_mm_hr"] = rain_override

    # Call Python ML risk_engine
    result = risk_engine.predict_risk(
        point=loc_data,
        population_data={"registered_population": loc_data["population_exposure"]}
    )

    return result

@app.post("/api/route")
def calculate_route(req: RouteRequest):
    """Calculates NetworkX safe evacuation route and rerouting logic."""
    router = evacuation_router.EvacuationRouter()
    
    if req.road_a_failed:
        router.update_edge_risk("road_a", 0.86)
        
    route_info = router.find_safest_route(req.origin, req.destination)
    return {
        "status": "SUCCESS",
        "active_route": route_info.get("route_name", "Gaurikund High Ridge Bypass" if req.road_a_failed else "NH-107 Highway"),
        "is_rerouted": req.road_a_failed,
        "eta_min": 21 if req.road_a_failed else 18,
        "explanation": "Road A exceeded critical flood risk (0.86). Automatically rerouted via Gaurikund Bypass." if req.road_a_failed else "NH-107 Highway is clear and safe for evacuation."
    }

@app.get("/api/scenarios")
def get_available_scenarios():
    """Returns scenarios configured in config.py."""
    return {
        "scenarios": [
            {"id": "NORMAL", "name": "01 - NORMAL MONSOON BASELINE"},
            {"id": "HEAVY_RAIN", "name": "02 - HEAVY RAINFALL IN UPPER BASIN"},
            {"id": "STORM_INTENSIFYING", "name": "03 - RAPIDLY INTENSIFYING STORM"},
            {"id": "ROAD_FAILURE", "name": "04 - NH-107 ROAD BREACH & REROUTE"},
            {"id": "SENSOR_FAILURE", "name": "05 - RADAR SENSOR #08 DEGRADATION"}
        ]
    }

# Mount static files (serves index.html, style.css, app.js directly on root)
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("Starting FLOODX Python ML Server on http://localhost:8000 ...")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
