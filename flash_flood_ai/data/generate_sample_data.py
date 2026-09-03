"""
generate_sample_data.py — Physically-Correlated Synthetic Data Generator
=========================================================================

Generates time-series observations for 12 locations across 8 scenarios in
a simulated mountain valley.  Physical correlations are enforced:

- High rainfall → increasing river level, soil saturation, runoff
- Steep slopes → faster runoff
- Upstream rainfall → downstream river rise (with time lag)
- Sensor failure → NaN injections

Output: ``sample_timeseries.csv`` with 15-minute interval observations.

IMPORTANT: This is SYNTHETIC data for pipeline testing and demonstration.
Model performance on this data does NOT represent real-world accuracy.
"""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

# Ensure the project root is on sys.path for imports
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from model.config import RANDOM_SEED

np.random.seed(RANDOM_SEED)


# ── Location definitions ──────────────────────────────────────────────────

LOCATIONS: list[dict[str, Any]] = [
    # Upstream (high altitude, steep slopes, low population)
    {"id": "upstream_01", "name": "Glacier View Station",  "lat": 33.45, "lng": 75.60, "slope_deg": 38, "altitude_m": 3200, "zone": "upstream",   "population": 200,  "tourist_pop": 50,   "elderly_frac": 0.08, "children_frac": 0.15, "historical_incident_density": 2.1},
    {"id": "upstream_02", "name": "Pine Ridge Outpost",    "lat": 33.43, "lng": 75.63, "slope_deg": 35, "altitude_m": 3050, "zone": "upstream",   "population": 350,  "tourist_pop": 100,  "elderly_frac": 0.10, "children_frac": 0.18, "historical_incident_density": 3.0},
    {"id": "upstream_03", "name": "Eagle Cliff Village",   "lat": 33.41, "lng": 75.58, "slope_deg": 42, "altitude_m": 3400, "zone": "upstream",   "population": 120,  "tourist_pop": 30,   "elderly_frac": 0.12, "children_frac": 0.20, "historical_incident_density": 4.5},
    {"id": "upstream_04", "name": "Snowmelt Creek Base",   "lat": 33.44, "lng": 75.65, "slope_deg": 30, "altitude_m": 2900, "zone": "upstream",   "population": 280,  "tourist_pop": 80,   "elderly_frac": 0.09, "children_frac": 0.16, "historical_incident_density": 1.8},

    # Mid-valley (moderate slopes, moderate population)
    {"id": "midvalley_01", "name": "Valley Temple Town",   "lat": 33.38, "lng": 75.68, "slope_deg": 22, "altitude_m": 2400, "zone": "midvalley", "population": 1800, "tourist_pop": 500,  "elderly_frac": 0.12, "children_frac": 0.22, "historical_incident_density": 5.2},
    {"id": "midvalley_02", "name": "Bridge Market Colony",  "lat": 33.36, "lng": 75.71, "slope_deg": 18, "altitude_m": 2200, "zone": "midvalley", "population": 2500, "tourist_pop": 300,  "elderly_frac": 0.14, "children_frac": 0.20, "historical_incident_density": 6.1},
    {"id": "midvalley_03", "name": "River Bend Settlement", "lat": 33.37, "lng": 75.66, "slope_deg": 25, "altitude_m": 2300, "zone": "midvalley", "population": 900,  "tourist_pop": 200,  "elderly_frac": 0.11, "children_frac": 0.19, "historical_incident_density": 7.3},
    {"id": "midvalley_04", "name": "Pilgrim Rest Camp",     "lat": 33.35, "lng": 75.73, "slope_deg": 15, "altitude_m": 2100, "zone": "midvalley", "population": 600,  "tourist_pop": 2000, "elderly_frac": 0.06, "children_frac": 0.10, "historical_incident_density": 3.8},

    # Downstream (lower slopes, higher population)
    {"id": "downstream_01", "name": "Riverside Colony",     "lat": 33.31, "lng": 75.77, "slope_deg": 10, "altitude_m": 1800, "zone": "downstream", "population": 4200, "tourist_pop": 400,  "elderly_frac": 0.15, "children_frac": 0.25, "historical_incident_density": 8.0},
    {"id": "downstream_02", "name": "Lower Falls Township", "lat": 33.30, "lng": 75.80, "slope_deg": 8,  "altitude_m": 1700, "zone": "downstream", "population": 5500, "tourist_pop": 250,  "elderly_frac": 0.16, "children_frac": 0.24, "historical_incident_density": 6.5},
    {"id": "downstream_03", "name": "Delta Market Village",  "lat": 33.29, "lng": 75.75, "slope_deg": 12, "altitude_m": 1850, "zone": "downstream", "population": 3000, "tourist_pop": 150,  "elderly_frac": 0.13, "children_frac": 0.21, "historical_incident_density": 5.0},
    {"id": "downstream_04", "name": "Flood Plain Hamlet",    "lat": 33.28, "lng": 75.82, "slope_deg": 5,  "altitude_m": 1600, "zone": "downstream", "population": 2200, "tourist_pop": 100,  "elderly_frac": 0.18, "children_frac": 0.23, "historical_incident_density": 9.2},
]

# Time lag (in 15-min steps) for upstream rain to affect downstream river
UPSTREAM_LAG: dict[str, int] = {
    "upstream": 0,
    "midvalley": 3,   # ~45 min
    "downstream": 6,  # ~90 min
}


# ── Scenario definitions ─────────────────────────────────────────────────

def _scenario_normal(t: int, _total: int) -> dict:
    """Scenario 1: Normal dry conditions."""
    return {
        "base_rainfall": 2.0 + np.random.normal(0, 1),
        "river_base": 0.5,
        "storm_factor": 0.0,
    }


def _scenario_heavy_rain(t: int, total: int) -> dict:
    """Scenario 2: Heavy sustained rainfall."""
    progress = t / max(total - 1, 1)
    return {
        "base_rainfall": 25.0 + 15.0 * progress + np.random.normal(0, 3),
        "river_base": 0.8 + 1.5 * progress,
        "storm_factor": 0.6,
    }


def _scenario_cloudburst(t: int, total: int) -> dict:
    """Scenario 3: Rapidly intensifying cloudburst."""
    progress = t / max(total - 1, 1)
    # Exponential ramp-up peaking around 70% of the way through
    intensity = np.clip(np.exp(3.5 * progress - 1.5), 0, 1)
    return {
        "base_rainfall": 5.0 + 85.0 * intensity + np.random.normal(0, 5),
        "river_base": 0.6 + 3.5 * intensity,
        "storm_factor": intensity,
    }


def _scenario_saturated_soil(t: int, total: int) -> dict:
    """Scenario 4: Post-rain saturated soil (moderate rain on wet ground)."""
    return {
        "base_rainfall": 15.0 + np.random.normal(0, 3),
        "river_base": 1.2,
        "storm_factor": 0.3,
        "soil_boost": 0.35,  # pre-saturated
    }


def _scenario_rapid_river_rise(t: int, total: int) -> dict:
    """Scenario 5: Rapid river rise (upstream dam-like release)."""
    progress = t / max(total - 1, 1)
    river_surge = 0.0
    if progress > 0.3:
        river_surge = 3.5 * min(1.0, (progress - 0.3) / 0.3)
    return {
        "base_rainfall": 8.0 + np.random.normal(0, 2),
        "river_base": 0.7 + river_surge,
        "storm_factor": 0.2,
    }


def _scenario_sensor_failure(t: int, total: int) -> dict:
    """Scenario 6: Normal conditions but with sensor failures."""
    return {
        "base_rainfall": 20.0 + np.random.normal(0, 3),
        "river_base": 1.0,
        "storm_factor": 0.3,
        "inject_nan": True,
    }


def _scenario_upstream_storm(t: int, total: int) -> dict:
    """Scenario 7: Storm upstream → delayed downstream impact."""
    progress = t / max(total - 1, 1)
    # Heavy rain upstream that stops after 50%, downstream sees the effect later
    upstream_rain = 60.0 * max(0, 1 - abs(progress - 0.3) / 0.3)
    return {
        "base_rainfall": 5.0 + np.random.normal(0, 2),
        "river_base": 0.6,
        "storm_factor": 0.1,
        "upstream_rain_override": upstream_rain,
    }


def _scenario_multi_hazard(t: int, total: int) -> dict:
    """Scenario 8: Multi-hazard (rain + saturated soil + steep terrain)."""
    progress = t / max(total - 1, 1)
    return {
        "base_rainfall": 30.0 + 40.0 * progress + np.random.normal(0, 4),
        "river_base": 1.0 + 2.5 * progress,
        "storm_factor": 0.5 + 0.4 * progress,
        "soil_boost": 0.25,
    }


SCENARIOS: list[tuple[str, Any]] = [
    ("normal",              _scenario_normal),
    ("heavy_rain",          _scenario_heavy_rain),
    ("cloudburst",          _scenario_cloudburst),
    ("saturated_soil",      _scenario_saturated_soil),
    ("rapid_river_rise",    _scenario_rapid_river_rise),
    ("sensor_failure",      _scenario_sensor_failure),
    ("upstream_storm",      _scenario_upstream_storm),
    ("multi_hazard",        _scenario_multi_hazard),
]

# ── Generator ─────────────────────────────────────────────────────────────

def generate_timeseries(
    n_steps: int = 24,           # 6 hours at 15-min intervals
    output_path: str | None = None,
) -> list[dict[str, Any]]:
    """Generate synthetic time-series observations.

    Parameters
    ----------
    n_steps : int
        Number of 15-minute time steps per scenario.
    output_path : str | None
        CSV output path.  Defaults to ``data/sample_timeseries.csv``.

    Returns
    -------
    list[dict]
        All generated observations.
    """
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "sample_timeseries.csv")

    all_rows: list[dict[str, Any]] = []
    base_time = datetime(2025, 7, 15, 6, 0, 0)  # monsoon season morning

    for scenario_name, scenario_fn in SCENARIOS:
        # Track upstream rainfall history for delayed downstream effect
        upstream_rain_history: list[float] = []

        for step in range(n_steps):
            timestamp = base_time + timedelta(minutes=15 * step)
            params = scenario_fn(step, n_steps)

            # Get upstream rain for this step
            upstream_rain = params.get("upstream_rain_override", params["base_rainfall"])
            upstream_rain_history.append(max(0, upstream_rain))

            for loc in LOCATIONS:
                row = _generate_observation(
                    loc, step, n_steps, timestamp, scenario_name,
                    params, upstream_rain_history,
                )
                all_rows.append(row)

        # Advance base time for next scenario
        base_time += timedelta(hours=8)

    # Write CSV
    if all_rows:
        _write_csv(all_rows, output_path)
        print(f"Generated {len(all_rows)} observations -> {output_path}")

    return all_rows


def _generate_observation(
    loc: dict,
    step: int,
    total_steps: int,
    timestamp: datetime,
    scenario: str,
    params: dict,
    upstream_rain_history: list[float],
) -> dict[str, Any]:
    """Generate a single observation for one location at one time step."""

    zone = loc["zone"]
    slope = loc["slope_deg"]
    altitude = loc["altitude_m"]

    # Base rainfall varies by zone (upstream gets more during storms)
    zone_rain_factor = {"upstream": 1.2, "midvalley": 1.0, "downstream": 0.7}
    rainfall = max(0, params["base_rainfall"] * zone_rain_factor[zone]
                   + np.random.normal(0, 2))

    # Soil saturation: increases with rainfall, slope speeds drainage
    storm_f = params.get("storm_factor", 0)
    soil_base = 0.2 + 0.5 * storm_f + params.get("soil_boost", 0)
    soil_drainage = 0.005 * slope  # steeper → drains faster
    soil_saturation = np.clip(
        soil_base + 0.003 * rainfall - soil_drainage + np.random.normal(0, 0.02),
        0, 1,
    )

    # River level: affected by rainfall and upstream lag
    lag = UPSTREAM_LAG[zone]
    if lag > 0 and len(upstream_rain_history) > lag:
        lagged_rain = upstream_rain_history[-lag - 1]
    else:
        lagged_rain = rainfall

    river_base = params["river_base"]
    river_from_rain = 0.02 * lagged_rain * (1 + slope / 45.0)
    river_level = max(0, river_base + river_from_rain + np.random.normal(0, 0.05))

    # Population exposure (normalized)
    total_pop = loc["population"] + loc["tourist_pop"]
    pop_exposure = total_pop / 5000.0  # normalize

    # Build row
    row: dict[str, Any] = {
        "timestamp": timestamp.isoformat(),
        "scenario": scenario,
        "id": loc["id"],
        "name": loc["name"],
        "lat": loc["lat"],
        "lng": loc["lng"],
        "zone": zone,
        "slope_deg": slope,
        "altitude_m": altitude,
        "rainfall_mm_hr": round(rainfall, 2),
        "river_level_m": round(river_level, 2),
        "soil_saturation": round(soil_saturation, 4),
        "historical_incident_density": loc["historical_incident_density"],
        "population_exposure": round(pop_exposure, 4),
        "registered_population": loc["population"],
        "tourist_population": loc["tourist_pop"],
        "elderly_fraction": loc["elderly_frac"],
        "children_fraction": loc["children_frac"],
    }

    # Sensor failure injection (Scenario 6)
    if params.get("inject_nan") and np.random.random() < 0.15:
        fail_field = np.random.choice(["rainfall_mm_hr", "river_level_m", "soil_saturation"])
        row[fail_field] = None

    return row


def _write_csv(rows: list[dict], path: str) -> None:
    """Write rows to CSV."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ── CLI entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    rows = generate_timeseries()
    print(f"\nTotal rows: {len(rows)}")
    print(f"Locations:  {len(LOCATIONS)}")
    print(f"Scenarios:  {len(SCENARIOS)}")
    print(f"Steps/scenario: 24 (6 hours at 15-min intervals)")

    # Summary statistics
    rainfalls = [r["rainfall_mm_hr"] for r in rows if r["rainfall_mm_hr"] is not None]
    rivers = [r["river_level_m"] for r in rows if r["river_level_m"] is not None]
    print(f"\nRainfall:  min={min(rainfalls):.1f}  max={max(rainfalls):.1f}  mean={sum(rainfalls)/len(rainfalls):.1f} mm/hr")
    print(f"River:     min={min(rivers):.1f}  max={max(rivers):.1f}  mean={sum(rivers)/len(rivers):.1f} m")
    nans = sum(1 for r in rows if r["rainfall_mm_hr"] is None or r["river_level_m"] is None)
    print(f"NaN cells: {nans} (sensor failure scenario)")
