"""
evacuation_router.py — Dynamic Safest-Route Evacuation Engine
==============================================================

Uses NetworkX for graph-based routing that minimizes:

    travel_time + α × current_risk_penalty + β × predicted_future_risk_penalty

Supports:
- Predictive routing (considers future road risk at estimated arrival time)
- Dynamic rerouting (recomputes when edges become unsafe)
- Evacuation priority ranking
- Graceful handling of disconnected graphs / no shelter reachable

Never crashes if an edge disappears or no safe route exists.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from model import config


# ── Public interface ───────────────────────────────────────────────────────

def build_road_graph(edges: list[dict[str, Any]]) -> nx.Graph:
    """Build a road graph from edge definitions.

    Parameters
    ----------
    edges : list[dict]
        Each dict must contain:
        ``from``, ``to``, ``distance``, ``travel_time``,
        ``current_risk``, ``predicted_risk``, ``road_status``.

    Returns
    -------
    nx.Graph
    """
    G = nx.Graph()
    for e in edges:
        attrs = {
            "distance": e.get("distance", 1.0),
            "travel_time": e.get("travel_time", 5.0),
            "current_risk": e.get("current_risk", 0.0),
            "predicted_risk": e.get("predicted_risk", 0.0),
            "road_status": e.get("road_status", "OPEN"),
        }
        G.add_edge(e["from"], e["to"], **attrs)
    return G


def get_safe_route(
    origin: str,
    shelter: str,
    risk_map: dict[str, float] | None = None,
    graph: nx.Graph | None = None,
) -> dict:
    """Find the safest evacuation route from *origin* to *shelter*.

    Parameters
    ----------
    origin : str
        Node ID of the starting location.
    shelter : str
        Node ID of the target shelter.
    risk_map : dict[str, float] | None
        Optional edge-risk overrides: ``{edge_key: risk_value}``.
        Edge keys are ``"from--to"`` (sorted alphabetically).
    graph : nx.Graph | None
        Road graph.  If ``None``, returns an error result.

    Returns
    -------
    dict
        ``route``         – list of node IDs
        ``total_time``    – estimated travel time (minutes)
        ``total_distance``– total distance
        ``total_cost``    – routing cost (time + risk penalty)
        ``max_edge_risk`` – highest risk on any edge of the route
        ``route_edges``   – list of edge details
        ``status``        – "OK" | "NO_ROUTE" | "NO_GRAPH"
        ``reason``        – human-readable status description
    """
    if graph is None or graph.number_of_edges() == 0:
        return _no_route("NO_GRAPH", "No road graph is available.")

    if origin not in graph:
        return _no_route("NO_ROUTE", f"Origin '{origin}' not found in road graph.")
    if shelter not in graph:
        return _no_route("NO_ROUTE", f"Shelter '{shelter}' not found in road graph.")

    # Apply risk-map overrides
    g = _apply_risk_map(graph, risk_map)

    # Build a working copy with blocked edges removed
    g_work = _remove_blocked_edges(g)

    if origin not in g_work or shelter not in g_work:
        return _no_route(
            "NO_ROUTE",
            "Origin or shelter became unreachable after removing blocked roads.",
        )

    # Check connectivity
    if not nx.has_path(g_work, origin, shelter):
        return _no_route(
            "NO_ROUTE",
            f"No viable evacuation route from '{origin}' to '{shelter}'. "
            "All paths are blocked or flooded.",
        )

    # Dijkstra with combined cost
    try:
        path = nx.dijkstra_path(g_work, origin, shelter, weight="_route_cost")
    except nx.NetworkXNoPath:
        return _no_route("NO_ROUTE", "No safe path found.")

    # Collect route details
    edges_detail = []
    total_time = 0.0
    total_dist = 0.0
    total_cost = 0.0
    max_risk = 0.0

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        data = g_work[u][v]
        edge_time = data.get("travel_time", 5.0)
        edge_dist = data.get("distance", 1.0)
        edge_risk = data.get("current_risk", 0.0)
        pred_risk = data.get("predicted_risk", 0.0)
        cost = data.get("_route_cost", edge_time)

        total_time += edge_time
        total_dist += edge_dist
        total_cost += cost
        max_risk = max(max_risk, edge_risk, pred_risk)

        edges_detail.append({
            "from": u,
            "to": v,
            "travel_time": edge_time,
            "distance": edge_dist,
            "current_risk": edge_risk,
            "predicted_risk": pred_risk,
            "road_status": data.get("road_status", "OPEN"),
        })

    return {
        "route": path,
        "total_time": round(total_time, 2),
        "total_distance": round(total_dist, 2),
        "total_cost": round(total_cost, 2),
        "max_edge_risk": round(max_risk, 4),
        "route_edges": edges_detail,
        "status": "OK",
        "reason": "Safe route found.",
    }


def simulate_risk_change(
    risk_map: dict[str, float],
    edge: tuple[str, str],
    new_risk: float,
    graph: nx.Graph | None = None,
    origin: str | None = None,
    shelter: str | None = None,
    previous_route: list[str] | None = None,
) -> dict:
    """Simulate a risk change on an edge and recompute the route.

    Parameters
    ----------
    risk_map : dict
        Current edge risk map.
    edge : tuple[str, str]
        The edge whose risk changed.
    new_risk : float
        The new risk value for this edge.
    graph : nx.Graph | None
        Road graph.
    origin : str | None
        Origin node for rerouting.
    shelter : str | None
        Shelter node for rerouting.
    previous_route : list[str] | None
        Previous route for comparison.

    Returns
    -------
    dict
        ``rerouted``       – bool
        ``reason``         – why route changed
        ``previous_route`` – list of node IDs
        ``new_route``      – list of node IDs
        ``new_route_detail``– full route detail dict
    """
    # Update risk map
    edge_key = _edge_key(edge[0], edge[1])
    updated_map = dict(risk_map)
    updated_map[edge_key] = new_risk

    if graph is None or origin is None or shelter is None:
        return {
            "rerouted": False,
            "reason": "Insufficient parameters for rerouting.",
            "previous_route": previous_route,
            "new_route": None,
            "new_route_detail": None,
        }

    # Recompute route
    new_result = get_safe_route(origin, shelter, updated_map, graph)

    new_route = new_result.get("route")
    rerouted = (
        previous_route is not None
        and new_route is not None
        and new_route != previous_route
    )

    reason = ""
    if new_result["status"] == "NO_ROUTE":
        reason = new_result["reason"]
    elif rerouted:
        reason = (
            f"Edge {edge[0]}-{edge[1]} exceeded critical flood-risk threshold "
            f"(risk={new_risk:.2f}). Route recalculated."
        )
    elif new_route == previous_route:
        reason = "Risk change did not affect the optimal route."

    return {
        "rerouted": rerouted,
        "reason": reason,
        "previous_route": previous_route,
        "new_route": new_route,
        "new_route_detail": new_result,
    }


def compute_evacuation_priority(
    locations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Rank locations by evacuation urgency.

    Parameters
    ----------
    locations : list[dict]
        Each dict is a ``predict_risk()`` output, optionally enriched with
        ``estimated_time_to_critical_min`` and ``population_data``.

    Returns
    -------
    list[dict]
        Sorted by priority (highest urgency first).  Each dict is augmented
        with ``evacuation_priority`` (1 = most urgent).
    """
    scored = []
    for loc in locations:
        risk = loc.get("risk_score", 0)
        t2c = loc.get("estimated_time_to_critical_min")
        pop_exp = loc.get("population_exposure", 0) or 0
        vuln = loc.get("vulnerability_score", 0.5)

        # Urgency increases with risk, population, vulnerability,
        # and decreases with time-to-critical
        time_factor = 1.0
        if t2c is not None and t2c > 0:
            time_factor = max(0.1, 1.0 - t2c / 120.0)  # closer = more urgent
        elif t2c == 0:
            time_factor = 1.0

        priority_score = (
            0.40 * risk
            + 0.25 * time_factor
            + 0.20 * min(1.0, pop_exp / 5.0)
            + 0.15 * vuln
        )

        scored.append({
            **loc,
            "_priority_score": round(priority_score, 4),
        })

    scored.sort(key=lambda x: x["_priority_score"], reverse=True)

    result = []
    for rank, loc in enumerate(scored, 1):
        loc_copy = dict(loc)
        loc_copy["evacuation_priority"] = rank
        loc_copy.pop("_priority_score", None)
        result.append(loc_copy)

    return result


# ── Sample graph for demonstration ────────────────────────────────────────

def create_sample_graph() -> tuple[nx.Graph, list[dict]]:
    """Create a sample road network for demonstration.

    Returns the graph and the edge definitions.

    Network layout (approximate mountain valley):

        U1 ──── U2
        │ ╲      │
        │   M1 ──│── M2
        │  / │╲  │  / │
        U3   │  M3   │
         ╲   │ / │╲  │
          D1─┤  │  D2
           ╲ │  │ /
            S1  S2
              ╲/
              S3

    U = upstream, M = midstream, D = downstream, S = shelter
    """
    edges = [
        # Upstream connections
        {"from": "U1", "to": "U2", "distance": 3.0, "travel_time": 8, "current_risk": 0.1, "predicted_risk": 0.15, "road_status": "OPEN"},
        {"from": "U1", "to": "M1", "distance": 4.0, "travel_time": 12, "current_risk": 0.2, "predicted_risk": 0.25, "road_status": "OPEN"},
        {"from": "U1", "to": "U3", "distance": 2.5, "travel_time": 7, "current_risk": 0.15, "predicted_risk": 0.2, "road_status": "OPEN"},
        {"from": "U2", "to": "M2", "distance": 3.5, "travel_time": 10, "current_risk": 0.1, "predicted_risk": 0.15, "road_status": "OPEN"},
        {"from": "U2", "to": "M3", "distance": 5.0, "travel_time": 15, "current_risk": 0.1, "predicted_risk": 0.1, "road_status": "OPEN"},

        # Midstream connections
        {"from": "M1", "to": "M2", "distance": 2.0, "travel_time": 6, "current_risk": 0.25, "predicted_risk": 0.3, "road_status": "OPEN"},
        {"from": "M1", "to": "M3", "distance": 3.0, "travel_time": 9, "current_risk": 0.2, "predicted_risk": 0.25, "road_status": "OPEN"},
        {"from": "M1", "to": "D1", "distance": 2.5, "travel_time": 7, "current_risk": 0.3, "predicted_risk": 0.4, "road_status": "OPEN"},
        {"from": "M2", "to": "D2", "distance": 3.0, "travel_time": 8, "current_risk": 0.2, "predicted_risk": 0.25, "road_status": "OPEN"},
        {"from": "M3", "to": "D1", "distance": 2.0, "travel_time": 6, "current_risk": 0.25, "predicted_risk": 0.35, "road_status": "OPEN"},
        {"from": "M3", "to": "D2", "distance": 2.5, "travel_time": 7, "current_risk": 0.15, "predicted_risk": 0.2, "road_status": "OPEN"},

        # Downstream to shelters
        {"from": "D1", "to": "S1", "distance": 1.5, "travel_time": 4, "current_risk": 0.2, "predicted_risk": 0.3, "road_status": "OPEN"},
        {"from": "D1", "to": "S2", "distance": 3.0, "travel_time": 8, "current_risk": 0.15, "predicted_risk": 0.2, "road_status": "OPEN"},
        {"from": "D2", "to": "S2", "distance": 2.0, "travel_time": 5, "current_risk": 0.1, "predicted_risk": 0.15, "road_status": "OPEN"},
        {"from": "D2", "to": "S3", "distance": 2.5, "travel_time": 6, "current_risk": 0.1, "predicted_risk": 0.1, "road_status": "OPEN"},
        {"from": "S1", "to": "S3", "distance": 4.0, "travel_time": 10, "current_risk": 0.05, "predicted_risk": 0.05, "road_status": "OPEN"},

        # Cross connections
        {"from": "U3", "to": "D1", "distance": 3.5, "travel_time": 10, "current_risk": 0.3, "predicted_risk": 0.45, "road_status": "OPEN"},
        {"from": "U3", "to": "M1", "distance": 2.0, "travel_time": 6, "current_risk": 0.2, "predicted_risk": 0.25, "road_status": "OPEN"},
        {"from": "M3", "to": "S2", "distance": 3.5, "travel_time": 9, "current_risk": 0.1, "predicted_risk": 0.15, "road_status": "OPEN"},
    ]

    graph = build_road_graph(edges)
    return graph, edges


# ── Internal helpers ──────────────────────────────────────────────────────

def _edge_key(u: str, v: str) -> str:
    """Canonical edge key (sorted)."""
    return "--".join(sorted([u, v]))


def _apply_risk_map(
    graph: nx.Graph,
    risk_map: dict[str, float] | None,
) -> nx.Graph:
    """Return a copy of *graph* with risk-map overrides applied."""
    g = graph.copy()

    if risk_map:
        for u, v, data in g.edges(data=True):
            key = _edge_key(u, v)
            if key in risk_map:
                data["current_risk"] = risk_map[key]

    # Compute composite routing cost for each edge
    alpha = config.ROUTING_RISK_PENALTY_ALPHA
    beta = config.ROUTING_PREDICTED_RISK_PENALTY_BETA

    for u, v, data in g.edges(data=True):
        time = data.get("travel_time", 5.0)
        cur_risk = data.get("current_risk", 0.0)
        pred_risk = data.get("predicted_risk", 0.0)
        data["_route_cost"] = time + alpha * cur_risk + beta * pred_risk

    return g


def _remove_blocked_edges(graph: nx.Graph) -> nx.Graph:
    """Remove edges that are blocked or exceed the critical risk threshold."""
    g = graph.copy()
    threshold = config.CRITICAL_ROAD_RISK_THRESHOLD

    to_remove = []
    for u, v, data in g.edges(data=True):
        if data.get("road_status") == "BLOCKED":
            to_remove.append((u, v))
        elif data.get("current_risk", 0) >= threshold:
            to_remove.append((u, v))

    g.remove_edges_from(to_remove)
    return g


def _no_route(status: str, reason: str) -> dict:
    """Return a no-route result."""
    return {
        "route": None,
        "total_time": None,
        "total_distance": None,
        "total_cost": None,
        "max_edge_risk": None,
        "route_edges": [],
        "status": status,
        "reason": reason,
    }
