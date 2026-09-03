# Flash Flood AI — Model Architecture & Technical Documentation

## Problem

Flash floods in mountainous regions of India are among the deadliest natural disasters. They develop within **minutes to a few hours** from triggers including cloudbursts, extreme short-duration rainfall, rapid glacial melt, saturated soil, and sudden upstream runoff.

Prediction is extremely difficult because:
- **Sparse sensors** — many valleys have zero automated gauges
- **Rapid onset** — conditions can become lethal in under 30 minutes
- **Complex terrain** — steep slopes, narrow valleys, and variable soil amplify hazard nonlinearly
- **Dynamic populations** — tourist/pilgrim populations fluctuate seasonally by 10×
- **Poor connectivity** — intermittent power, cellular, and internet

Traditional flood forecasting systems (designed for large river basins with days of lead time) are fundamentally unsuited for this problem.

---

## Solution

An AI-powered **local disaster-intelligence engine** that:

1. **Forecasts** how flood risk will evolve at each location over the next 15–120 minutes
2. **Estimates uncertainty** and degrades gracefully when sensors fail
3. **Identifies who is most exposed** using dynamic population modeling
4. **Predicts time-to-danger** for each location
5. **Continuously determines the safest evacuation routes** considering future predicted road risk
6. **Automatically reroutes** when conditions change
7. **Explains every prediction** in human-readable terms

---

## AI Architecture

```
Multi-source sensor data
        ↓
Data Validation & Anomaly Detection     (anomaly_detector.py)
        ↓
Spatiotemporal Feature Engineering       (feature_engineering.py)
        ↓
Hazard Forecasting (Baseline / ML)       (risk_engine.py, forecasting_model.py)
        ↓
Vulnerability & Exposure Assessment      (risk_engine.py)
        ↓
Risk + Uncertainty Estimation            (uncertainty.py)
        ↓
Time-to-Danger Prediction                (forecasting_model.py)
        ↓
Explainable AI                           (explainability.py)
        ↓
Evacuation Priority Ranking              (evacuation_router.py)
        ↓
Dynamic Safest-Route Optimization        (evacuation_router.py)
        ↓
Actionable Warning
```

### Risk Model

Risk is computed as a **geometric-mean-weighted combination**:

```
risk = hazard^0.60 × exposure^0.25 × vulnerability^0.15
```

This ensures hazard dominates while exposure and vulnerability meaningfully shift the score. Unlike raw multiplication, this formulation avoids collapsing scores to zero when any single component is low.

### Dual Model Architecture

| Model | Purpose | When Used |
|-------|---------|-----------|
| **Explainable Baseline** | Transparent weighted sum with named, configurable weights | Always available — cold start, fallback, interpretability |
| **Random Forest ML** | Learns nonlinear relationships from temporal features | When trained model exists and `MODEL_MODE="ml"` |

Both models share the **same interface** — the frontend never needs to know which is running.

### Temporal Forecasting

Forecasts risk at **15, 30, 60, and 120 minute** horizons using trend extrapolation (rate + acceleration) of key variables. The architecture supports future replacement with LSTM, Temporal Transformer, or TFT.

### Uncertainty Estimation

Every prediction includes a confidence score computed from:
- **Data quality** (30%) — from anomaly detection
- **Feature completeness** (25%) — fraction of non-missing features
- **Model uncertainty** (25%) — RF tree prediction variance
- **Signal agreement** (20%) — whether rainfall, river, and soil trends agree

---

## Key Differentiators

1. **Predictive, not purely reactive** — forecasts future risk, not just current conditions
2. **Hyperlocal** — per-location predictions, not regional averages
3. **Spatiotemporal** — uses rolling windows, rates, accelerations, not isolated snapshots
4. **Upstream-aware** — rainfall upstream becomes a downstream threat (with configurable lag)
5. **Vulnerability-aware** — elderly, children, hospital populations weighted more heavily
6. **Dynamic population-aware** — tourists, pilgrims, seasonal workers tracked separately
7. **Explainable by default** — every prediction includes human-readable reasoning
8. **Uncertainty-aware** — confidence reflects actual data quality and model agreement
9. **Predictive evacuation routing** — routes consider future road risk, not just current
10. **Dynamic rerouting** — automatically finds new routes when roads become unsafe
11. **Sensor anomaly tolerance** — gracefully degrades with missing/faulty sensors
12. **Edge-deployable architecture** — no GPU, no cloud dependency, runs on Raspberry Pi
13. **Graceful ML fallback** — baseline always available when ML model fails

---

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `config.py` | All thresholds, weights, bounds, hyperparameters |
| `anomaly_detector.py` | Sensor validation, impossible values, jumps, staleness |
| `feature_engineering.py` | Rolling windows, rates, accelerations, upstream features |
| `risk_engine.py` | Unified predict_risk() — dispatches baseline/ML, combines H×E×V |
| `forecasting_model.py` | Multi-horizon forecasting, time-to-danger estimation |
| `uncertainty.py` | Confidence, data quality, model uncertainty, signal agreement |
| `explainability.py` | Factor analysis, change explanation, counterfactual reasoning |
| `evacuation_router.py` | NetworkX routing, predictive route selection, dynamic rerouting |

---

## Software Interfaces

```python
# Risk prediction
predict_risk(point: dict, history=None, upstream_data=None, population_data=None) -> dict

# Temporal forecasting
forecast_risk(timeseries: list[dict], horizons=[15,30,60,120]) -> dict

# Safe routing
get_safe_route(origin: str, shelter: str, risk_map: dict, graph: nx.Graph) -> dict

# Dynamic rerouting
simulate_risk_change(risk_map: dict, edge: tuple, new_risk: float, ...) -> dict

# Data validation
validate_input(point: dict) -> dict
```

---

## AI vs Rules — Clear Distinction

| Component | Type | Purpose |
|-----------|------|---------|
| Weighted hazard baseline | **Rule-based** | Fallback, explainability, cold start, no-data scenarios |
| Random Forest hazard model | **Trained ML** | Learning nonlinear relationships, temporal forecasting |
| Anomaly detection | **Rule-based** | Sensor validation (pluggable for future ML) |
| Feature engineering | **Deterministic** | Reproducible, testable feature computation |
| Trend extrapolation | **Statistical** | Baseline forecasting when ML unavailable |
| Routing optimization | **Graph algorithm** | Dijkstra with composite cost function |

The rule-based baseline is **not called "AI"**. It exists for reliability and transparency.

---

## Production Deployment Roadmap

### Data Sources for Real Deployment

| Source | Data | Status |
|--------|------|--------|
| IMD (India Meteorological Department) | Weather forecasts, radar | Integration ready |
| Central Water Commission | River gauge levels | Adapter interface designed |
| ISRO/NRSC | Satellite precipitation, DEM | Adapter interface designed |
| data.gov.in | Census, road network, disaster history | Adapter interface designed |
| IoT sensors | Local rain gauges, soil moisture, river level | Adapter interface designed |
| Weather radar | Reflectivity, precipitation estimation | Future integration |

### Staged Upgrade Path

| Stage | Capability | Requirement |
|-------|-----------|-------------|
| 1 ✅ | Rule engine + Random Forest | Synthetic data (current) |
| 2 | Temporal deep learning (LSTM/Transformer) | Historical labeled data |
| 3 | Satellite/radar integration | ISRO/IMD data access |
| 4 | River-network graph modeling | Hydrological survey data |
| 5 | Spatiotemporal GNN | Graph + temporal labeled data |
| 6 | Edge inference (Raspberry Pi) | Model compression/quantization |
| 7 | Continual learning | Feedback loop infrastructure |

### Edge Deployment Architecture

```
Low-cost sensors → Edge device → Local inference → Local warning
                                      ↓
                            Intermittent sync → Central dashboard
```

The system does **not** fundamentally depend on continuous cloud connectivity.

---

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Generate sample data
python -m data.generate_sample_data

# Run integration demos
python -m model.test_demo

# Run unit tests
python -m pytest tests/ -v
```

---

## Known Limitations

- All performance metrics are on **synthetic data only** — not real-world validated
- Upstream graph is simplified (not a real river network)
- Population data is manually configured
- Probability calibration requires real labeled data
- SHAP not included (unnecessary dependency for prototype)
- Deep learning models documented but not implemented (insufficient data)
