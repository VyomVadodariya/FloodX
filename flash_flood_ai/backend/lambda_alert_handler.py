"""
lambda_alert_handler.py — Orchestration API for End-to-End Pipeline
===================================================================

Accepts an incoming sensor payload, runs it through the core Risk Engine,
computes dynamic evacuation routing if the risk is HIGH/CRITICAL, 
generates a GenAI emergency alert using Bedrock, logs everything to MongoDB,
and returns the final composite JSON.
"""

from __future__ import annotations

import json
import logging
import traceback
from typing import Any

from backend.mongodb import FloodXDatabase
from backend.lambda_risk_handler import lambda_handler as risk_handler
from backend.lambda_route_handler import lambda_handler as route_handler
from backend.bedrock_alerts import BedrockAlertGenerator

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """End-to-End Orchestration Handler."""
    try:
        if "body" in event:
            body = json.loads(event["body"])
        else:
            body = event
            
        location_id = body.get("id")
        if not location_id:
            return _respond(400, {"error": "Missing required field 'id'."})

        # 1. Run Risk Engine
        # We invoke the handler directly (in AWS this might be an EventBridge/SQS flow, 
        # but for prototype we orchestrate synchronously).
        risk_response = risk_handler(body, context)
        
        if risk_response["statusCode"] != 200:
            return risk_response # Propagate error
            
        risk_data = json.loads(risk_response["body"]).get("data", {})
        risk_label = risk_data.get("risk_label", "UNKNOWN")
        
        # 2. Dynamic Routing (Only if HIGH or CRITICAL)
        routing_data = None
        if risk_label in ("HIGH", "CRITICAL"):
            route_payload = {"start_location": location_id}
            route_response = route_handler(route_payload, context)
            if route_response["statusCode"] == 200:
                routing_data = json.loads(route_response["body"]).get("routing")

        # 3. Generate Alert
        alert_response = BedrockAlertGenerator.generate_alert(risk_data, routing_data)
        
        if alert_response.get("status") in ("success", "fallback"):
            # 4. Store Alert Log
            alert_doc = {
                "location_id": location_id,
                "risk_label": risk_label,
                "alert_content": alert_response["alert"]
            }
            FloodXDatabase.store_alert_log(alert_doc)
            
        # 5. Build final response
        return _respond(200, {
            "orchestration_status": "success",
            "location_id": location_id,
            "risk_assessment": risk_data,
            "evacuation_routing": routing_data,
            "emergency_alert": alert_response.get("alert")
        })

    except Exception as e:
        logger.error(f"Alert Orchestration failed: {traceback.format_exc()}")
        return _respond(500, {"error": str(e)})


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
