# AI-Powered Hyperlocal Flash-Flood Intelligence & Evacuation System

> **Prototype / demonstration model** — designed for real deployment, running on synthetic data.

## What This Does

A local disaster-intelligence engine for hilly/mountainous regions of India that answers:

- **Where is danger increasing?** — Per-location hazard forecasting
- **How dangerous will it become?** — Risk forecasting at 15/30/60/120 min horizons
- **When is it likely to become critical?** — Time-to-danger estimation
- **Why does the model believe that?** — Explainable predictions with top factors
- **How certain is the prediction?** — Uncertainty-aware confidence scoring
- **How many people are exposed?** — Dynamic population vulnerability assessment
- **Which locations should be evacuated first?** — Priority ranking
- **Which evacuation route is safest?** — Predictive routing considering future road risk
- **What if a road becomes flooded?** — Automatic dynamic rerouting
- **Can it work when sensors fail?** — Graceful degradation with data-quality warnings

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Generate synthetic data
cd flash_flood_ai
python -m data.generate_sample_data

# Run the full integration demo (8 scenarios)
python -m model.test_demo

# Run unit tests
python -m pytest tests/ -v
```

## Project Structure

```
flash_flood_ai/
├── data/
│   ├── generate_sample_data.py    # Physically-correlated data generator
│   ├── sample_timeseries.csv      # Generated time-series (auto-created)
│   └── README.md                  # Data schema documentation
├── model/
│   ├── config.py                  # All thresholds, weights, parameters
│   ├── risk_engine.py             # Unified risk prediction (baseline + ML)
│   ├── feature_engineering.py     # Spatiotemporal features
│   ├── forecasting_model.py       # Multi-horizon forecasting
│   ├── uncertainty.py             # Confidence & data quality
│   ├── anomaly_detector.py        # Sensor validation & anomaly detection
│   ├── evacuation_router.py       # NetworkX predictive routing
│   ├── explainability.py          # Explanations & counterfactuals
│   ├── test_demo.py               # 8 integration demonstrations
│   └── README.md                  # Full technical documentation
├── tests/
│   ├── test_risk_engine.py        # Risk engine unit tests
│   ├── test_forecasting.py        # Feature engineering & forecast tests
│   └── test_router.py             # Routing engine unit tests
├── requirements.txt
└── README.md                      # This file
```

## Architecture

```
                    FLASH-FLOOD AI
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
       FORECAST        VULNERABILITY     UNCERTAINTY
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                    RISK INTELLIGENCE
                          │
               ┌──────────┴──────────┐
               ▼                     ▼
       EVACUATION PRIORITY      SAFE ROUTING
               │                     │
               └──────────┬──────────┘
                          ▼
                   DYNAMIC RESPONSE
```

## Dependencies

- `numpy`, `pandas`, `scikit-learn`, `networkx`, `joblib`, `pytest`
- No GPU required
- No internet required at runtime
- Runs on a standard laptop

## Documentation

See [`model/README.md`](model/README.md) for full technical documentation including:
- Detailed architecture
- Algorithm descriptions
- AI vs. rules distinction
- Production deployment roadmap
- Known limitations

## License

Prototype for educational / hackathon use.
