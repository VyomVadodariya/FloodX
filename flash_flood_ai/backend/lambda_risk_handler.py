"""
lambda_risk_handler.py — Primary AWS Lambda Entry Point for Risk Engine
=======================================================================

Serverless handler that:
1) Accepts incoming sensor data JSON
2) Stores raw reading to MongoDB Time-Series
3) Retrieves recent location history from MongoDB
4) Executes `predict_risk()` from the core AI engine
5) Saves prediction snapshot to MongoDB
6) Returns the structured JSON response

Features graceful degradation: if MongoDB is unreachable, it will still process
the single data point and return a prediction (with lower confidence due to
lack of history).
"""

from __future__ import annotations

import json
import logging
import traceback
from typing import Any

# AWS Lambda contexts remain warm, so importing models here keeps them in memory
from backend.mongodb import FloodXDatabase
from model.risk_engine import predict_risk

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for sensor data ingestion & risk prediction."""
    try:
        # 1. Parse incoming request
        if "body" in event:
            body = json.loads(event["body"])
        else:
            body = event  # Direct invocation testing
            
        if not isinstance(body, dict):
            return _respond(400, {"error": "Invalid request format. Expected JSON object."})
            
        location_id = body.get("id")
        if not location_id:
            return _respond(400, {"error": "Missing required field 'id'."})

        # 2. Store raw reading asynchronously-equivalent (fire-and-forget logic in a real async queue, but here synchronous)
        FloodXDatabase.store_sensor_reading(body)

        # 3. Retrieve temporal history and context
        history = FloodXDatabase.get_recent_history(location_id, limit=24)
        
        # In a full system, upstream data and population data would be fetched here
        # based on location_id from the database.
        # For prototype, we pass None to rely on fallback/default logic.
        upstream_data = None
        population_data = None
        previous_prediction = None # Could fetch latest risk_snapshot from MongoDB

        # 4. Execute AI Engine
        prediction = predict_risk(
            point=body,
            history=history,
            upstream_data=upstream_data,
            population_data=population_data,
            model_mode=None, # Use config default
            previous_prediction=previous_prediction,
        )

        # 5. Store Prediction Snapshot
        snapshot = {
            "location_id": location_id,
            "input_point": body,
            "prediction": prediction
        }
        FloodXDatabase.store_risk_snapshot(snapshot)

        # 6. Return standard response
        return _respond(200, {
            "status": "success",
            "message": "Risk intelligence processed.",
            "data": prediction
        })

    except Exception as e:
        logger.error(f"Lambda execution failed: {traceback.format_exc()}")
        # Fail gracefully
        return _respond(500, {
            "status": "error",
            "message": "Internal server error during risk processing.",
            "details": str(e)
        })


def _respond(status_code: int, payload: dict) -> dict:
    """Format standard API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(payload)
    }
