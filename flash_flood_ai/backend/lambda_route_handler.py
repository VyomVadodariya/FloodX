"""
lambda_route_handler.py — Dynamic Evacuation Routing API
========================================================

AWS Lambda handler that calculates the safest/fastest evacuation route
using a dynamic graph.
Edge weights represent travel time. If a node's hazard score exceeds
a critical threshold (e.g., 0.7), incident edges are severed (weight = infinity),
forcing the routing algorithm to find a safe detour.

Uses Dijkstra's algorithm.
"""

from __future__ import annotations

import json
import logging
import traceback
import heapq
from typing import Any

from backend.mongodb import FloodXDatabase

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── Mock Graph Definition ──────────────────────────────────────────────────
# In a real system, this would be loaded from MongoDB or a GIS system (e.g. PostGIS/pgRouting)

# Format: node_id -> list of (neighbor_id, base_travel_time_minutes)
BASE_GRAPH = {
    "downstream_01": [("midvalley_02", 15), ("safe_zone_alpha", 25)],
    "midvalley_02": [("upstream_01", 30), ("downstream_01", 15), ("safe_zone_beta", 20)],
    "upstream_01": [("midvalley_02", 30), ("safe_zone_gamma", 10)],
    "safe_zone_alpha": [("downstream_01", 25)],
    "safe_zone_beta": [("midvalley_02", 20)],
    "safe_zone_gamma": [("upstream_01", 10)],
}

SAFE_ZONES = {"safe_zone_alpha", "safe_zone_beta", "safe_zone_gamma"}

HAZARD_SEVER_THRESHOLD = 0.70


# ── Routing Logic ────────────────────────────────────────────────────────

def build_dynamic_graph(base_graph: dict, node_hazards: dict[str, float]) -> dict:
    """Sever edges connected to highly hazardous nodes."""
    dynamic_graph = {}
    for node, neighbors in base_graph.items():
        dynamic_graph[node] = []
        for neighbor, weight in neighbors:
            # If the destination node is too dangerous, the road is impassable
            dest_hazard = node_hazards.get(neighbor, 0.0)
            if dest_hazard >= HAZARD_SEVER_THRESHOLD:
                # Edge severed
                continue
            dynamic_graph[node].append((neighbor, weight))
    return dynamic_graph


def dijkstra_safest_route(graph: dict, start_node: str, safe_zones: set[str]) -> dict:
    """Find the fastest route to any safe zone using Dijkstra's algorithm."""
    if start_node in safe_zones:
        return {"status": "success", "route": [start_node], "travel_time": 0, "message": "Already in a safe zone."}

    # Priority queue stores (cumulative_time, current_node, path)
    pq = [(0, start_node, [start_node])]
    visited = set()

    while pq:
        current_time, current_node, path = heapq.heappop(pq)

        if current_node in safe_zones:
            return {
                "status": "success",
                "route": path,
                "travel_time": current_time,
                "destination": current_node
            }

        if current_node in visited:
            continue
            
        visited.add(current_node)

        for neighbor, travel_time in graph.get(current_node, []):
            if neighbor not in visited:
                heapq.heappush(pq, (current_time + travel_time, neighbor, path + [neighbor]))

    return {
        "status": "failed",
        "message": "No safe route available. Shelter in place immediately."
    }


# ── Lambda Entry Point ────────────────────────────────────────────────────

def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for dynamic evacuation routing."""
    try:
        if "body" in event:
            body = json.loads(event["body"])
        else:
            body = event
            
        start_location = body.get("start_location")
        if not start_location:
            return _respond(400, {"error": "Missing 'start_location'"})

        if start_location not in BASE_GRAPH:
            return _respond(404, {"error": f"Unknown location: {start_location}"})

        # Retrieve current risk snapshots for all nodes to build hazard map
        # In production, query the latest snapshots from MongoDB
        db = FloodXDatabase.get_db()
        node_hazards = {}
        if db:
            # Aggregate latest hazard score per location
            # (Mock implementation of latest state retrieval)
            for loc_id in BASE_GRAPH.keys():
                latest = db.risk_snapshots.find_one({"location_id": loc_id}, sort=[("timestamp", -1)])
                if latest and "prediction" in latest:
                    node_hazards[loc_id] = latest["prediction"].get("hazard_score", 0.0)
        
        # Build dynamic graph
        dynamic_graph = build_dynamic_graph(BASE_GRAPH, node_hazards)
        
        # Calculate route
        routing_result = dijkstra_safest_route(dynamic_graph, start_location, SAFE_ZONES)
        
        return _respond(200, {
            "start_location": start_location,
            "node_hazards": node_hazards,
            "routing": routing_result
        })

    except Exception as e:
        logger.error(f"Routing failed: {traceback.format_exc()}")
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
