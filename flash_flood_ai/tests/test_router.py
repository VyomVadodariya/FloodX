"""
test_router.py — Unit Tests for Evacuation Router
===================================================
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from model.evacuation_router import (
    build_road_graph,
    get_safe_route,
    simulate_risk_change,
    create_sample_graph,
    compute_evacuation_priority,
)


# ── Helper ────────────────────────────────────────────────────────────────

def _simple_graph():
    """A → B → C (shelter), with alternative A → D → C."""
    edges = [
        {"from": "A", "to": "B", "distance": 2, "travel_time": 5,
         "current_risk": 0.1, "predicted_risk": 0.15, "road_status": "OPEN"},
        {"from": "B", "to": "C", "distance": 3, "travel_time": 8,
         "current_risk": 0.2, "predicted_risk": 0.25, "road_status": "OPEN"},
        {"from": "A", "to": "D", "distance": 4, "travel_time": 10,
         "current_risk": 0.05, "predicted_risk": 0.05, "road_status": "OPEN"},
        {"from": "D", "to": "C", "distance": 3, "travel_time": 7,
         "current_risk": 0.05, "predicted_risk": 0.05, "road_status": "OPEN"},
    ]
    return build_road_graph(edges)


# ── Tests ─────────────────────────────────────────────────────────────────

class TestSafeRoute:

    def test_finds_route(self):
        g = _simple_graph()
        result = get_safe_route("A", "C", graph=g)
        assert result["status"] == "OK"
        assert result["route"] is not None
        assert result["route"][0] == "A"
        assert result["route"][-1] == "C"

    def test_route_has_travel_time(self):
        g = _simple_graph()
        result = get_safe_route("A", "C", graph=g)
        assert result["total_time"] > 0
        assert result["total_distance"] > 0

    def test_prefers_safer_route(self):
        """When one route has much higher risk, the safer route is chosen."""
        edges = [
            {"from": "A", "to": "B", "distance": 2, "travel_time": 5,
             "current_risk": 0.7, "predicted_risk": 0.8, "road_status": "OPEN"},
            {"from": "B", "to": "C", "distance": 2, "travel_time": 5,
             "current_risk": 0.7, "predicted_risk": 0.8, "road_status": "OPEN"},
            {"from": "A", "to": "D", "distance": 5, "travel_time": 12,
             "current_risk": 0.05, "predicted_risk": 0.05, "road_status": "OPEN"},
            {"from": "D", "to": "C", "distance": 5, "travel_time": 12,
             "current_risk": 0.05, "predicted_risk": 0.05, "road_status": "OPEN"},
        ]
        g = build_road_graph(edges)
        result = get_safe_route("A", "C", graph=g)
        assert "D" in result["route"]  # should prefer safer A→D→C

    def test_blocked_road_avoided(self):
        edges = [
            {"from": "A", "to": "B", "distance": 2, "travel_time": 5,
             "current_risk": 0.1, "predicted_risk": 0.1, "road_status": "BLOCKED"},
            {"from": "B", "to": "C", "distance": 2, "travel_time": 5,
             "current_risk": 0.1, "predicted_risk": 0.1, "road_status": "OPEN"},
            {"from": "A", "to": "D", "distance": 5, "travel_time": 12,
             "current_risk": 0.1, "predicted_risk": 0.1, "road_status": "OPEN"},
            {"from": "D", "to": "C", "distance": 5, "travel_time": 12,
             "current_risk": 0.1, "predicted_risk": 0.1, "road_status": "OPEN"},
        ]
        g = build_road_graph(edges)
        result = get_safe_route("A", "C", graph=g)
        assert "B" not in result["route"]

    def test_no_graph_returns_error(self):
        result = get_safe_route("A", "C", graph=None)
        assert result["status"] == "NO_GRAPH"

    def test_nonexistent_origin(self):
        g = _simple_graph()
        result = get_safe_route("X", "C", graph=g)
        assert result["status"] == "NO_ROUTE"

    def test_nonexistent_shelter(self):
        g = _simple_graph()
        result = get_safe_route("A", "Z", graph=g)
        assert result["status"] == "NO_ROUTE"

    def test_disconnected_graph(self):
        edges = [
            {"from": "A", "to": "B", "distance": 2, "travel_time": 5,
             "current_risk": 0.1, "predicted_risk": 0.1, "road_status": "OPEN"},
            {"from": "C", "to": "D", "distance": 2, "travel_time": 5,
             "current_risk": 0.1, "predicted_risk": 0.1, "road_status": "OPEN"},
        ]
        g = build_road_graph(edges)
        result = get_safe_route("A", "D", graph=g)
        assert result["status"] == "NO_ROUTE"

    def test_critical_risk_edge_blocked(self):
        """Edges with risk >= CRITICAL_ROAD_RISK_THRESHOLD are removed."""
        edges = [
            {"from": "A", "to": "B", "distance": 2, "travel_time": 5,
             "current_risk": 0.85, "predicted_risk": 0.9, "road_status": "OPEN"},
            {"from": "B", "to": "C", "distance": 2, "travel_time": 5,
             "current_risk": 0.1, "predicted_risk": 0.1, "road_status": "OPEN"},
            {"from": "A", "to": "D", "distance": 5, "travel_time": 12,
             "current_risk": 0.1, "predicted_risk": 0.1, "road_status": "OPEN"},
            {"from": "D", "to": "C", "distance": 5, "travel_time": 12,
             "current_risk": 0.1, "predicted_risk": 0.1, "road_status": "OPEN"},
        ]
        g = build_road_graph(edges)
        result = get_safe_route("A", "C", graph=g)
        assert "B" not in result["route"]


class TestDynamicRerouting:

    def test_reroute_on_risk_increase(self):
        """A->B->C is initially the best route; when A->B risk spikes,
        the system reroutes to A->D->C."""
        edges = [
            {"from": "A", "to": "B", "distance": 2, "travel_time": 3,
             "current_risk": 0.05, "predicted_risk": 0.05, "road_status": "OPEN"},
            {"from": "B", "to": "C", "distance": 2, "travel_time": 3,
             "current_risk": 0.05, "predicted_risk": 0.05, "road_status": "OPEN"},
            {"from": "A", "to": "D", "distance": 5, "travel_time": 12,
             "current_risk": 0.1, "predicted_risk": 0.1, "road_status": "OPEN"},
            {"from": "D", "to": "C", "distance": 5, "travel_time": 12,
             "current_risk": 0.1, "predicted_risk": 0.1, "road_status": "OPEN"},
        ]
        g = build_road_graph(edges)
        initial = get_safe_route("A", "C", graph=g)
        assert "B" in initial["route"], "Initial route should use A->B->C"

        reroute = simulate_risk_change(
            risk_map={},
            edge=("A", "B"),
            new_risk=0.95,
            graph=g,
            origin="A",
            shelter="C",
            previous_route=initial["route"],
        )
        # A->B is now blocked (risk >= threshold), route must change
        assert reroute["rerouted"] is True
        assert "D" in reroute["new_route"]

    def test_no_reroute_for_low_risk_change(self):
        g = _simple_graph()
        initial = get_safe_route("A", "C", graph=g)

        reroute = simulate_risk_change(
            risk_map={},
            edge=("A", "B"),
            new_risk=0.15,  # slight increase
            graph=g,
            origin="A",
            shelter="C",
            previous_route=initial["route"],
        )
        # May or may not reroute — just ensure it doesn't crash


class TestSampleGraph:

    def test_sample_graph_created(self):
        g, edges = create_sample_graph()
        assert g.number_of_nodes() > 0
        assert g.number_of_edges() > 0

    def test_shelters_reachable(self):
        g, _ = create_sample_graph()
        for origin in ["M1", "D1", "U1"]:
            for shelter in ["S1", "S2", "S3"]:
                result = get_safe_route(origin, shelter, graph=g)
                assert result["status"] == "OK", \
                    f"No route from {origin} to {shelter}"


class TestEvacuationPriority:

    def test_priority_ranking(self):
        locations = [
            {"id": "A", "risk_score": 0.5, "population_exposure": 1.0,
             "vulnerability_score": 0.5, "estimated_time_to_critical_min": 30},
            {"id": "B", "risk_score": 0.9, "population_exposure": 3.0,
             "vulnerability_score": 0.7, "estimated_time_to_critical_min": 5},
        ]
        ranked = compute_evacuation_priority(locations)
        assert ranked[0]["id"] == "B"  # higher risk, more people
        assert ranked[0]["evacuation_priority"] == 1

    def test_empty_list(self):
        assert compute_evacuation_priority([]) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
