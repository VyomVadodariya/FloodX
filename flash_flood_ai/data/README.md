# Flash Flood AI — Sample Data

## Overview

Synthetic time-series data for pipeline testing and demonstration.

**⚠ IMPORTANT: This is SYNTHETIC data. Model performance on this data does NOT represent real-world flood-prediction accuracy.**

## Schema

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | ISO datetime | Observation time (15-min intervals) |
| `scenario` | string | Scenario name (normal, heavy_rain, cloudburst, etc.) |
| `id` | string | Location identifier |
| `name` | string | Human-readable location name |
| `lat` / `lng` | float | Coordinates |
| `zone` | string | upstream / midvalley / downstream |
| `slope_deg` | float | Terrain slope (degrees) |
| `altitude_m` | float | Altitude (meters) |
| `rainfall_mm_hr` | float | Rainfall intensity (mm/hr) — may be `None` for sensor failure |
| `river_level_m` | float | River level (meters) — may be `None` |
| `soil_saturation` | float | 0–1 — may be `None` |
| `historical_incident_density` | float | Historical flood events per km² |
| `population_exposure` | float | Normalized population exposure |
| `registered_population` | int | Permanent residents |
| `tourist_population` | int | Tourist/transient population |
| `elderly_fraction` | float | Fraction of elderly population |
| `children_fraction` | float | Fraction of children population |

## Scenarios

1. **Normal** — Dry, low risk
2. **Heavy rain** — Sustained heavy rainfall
3. **Cloudburst** — Rapidly intensifying storm
4. **Saturated soil** — Moderate rain on pre-wetted ground
5. **Rapid river rise** — Upstream dam-like release
6. **Sensor failure** — Normal conditions with NaN injections
7. **Upstream storm** — Storm upstream with delayed downstream impact
8. **Multi-hazard** — Rain + saturated soil + steep terrain

## Physical Correlations

- High rainfall → increasing river level (with upstream time lag)
- High rainfall → increasing soil saturation
- Steep slopes → faster runoff → amplified river response
- Upstream rainfall → downstream river rise (delayed by ~45–90 min)

## Generation

```bash
cd flash_flood_ai
python -m data.generate_sample_data
```
