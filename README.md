# FloodX: AI-Powered Hyperlocal Flash-Flood Intelligence & Evacuation System

**FloodX** is a production-oriented disaster-intelligence and decision-support engine. It evolves traditional reactive flood classifiers into a proactive, uncertainty-aware, and explainable system designed for hilly and mountainous regions.

---

## 1. The Problem: Why Flash Floods Are Hard to Predict

Flash floods, particularly in mountainous terrain, are uniquely challenging to forecast compared to traditional river basin floods:
* **Rapid Onset:** Life-threatening conditions can develop in under 30 minutes from triggers like cloudbursts, intense short-duration rainfall, or rapid glacial melt.
* **Sparse Sensor Coverage:** Hilly valleys often lack dense automated gauge networks.
* **Complex Terrain:** Steep slopes, narrow channels, and highly variable soil saturation cause nonlinear hazard amplification.
* **Dynamic Exposure:** Population vulnerability fluctuates massively due to seasonal tourists, pilgrims, and temporary workers.
* **Communication Breakdown:** Poor connectivity (power/cellular drops) often severs the link between centralized forecasting and the actual danger zones.

Traditional forecasting systems built for large rivers with days of lead time fundamentally fail in these environments. 

---

## 2. The Solution: FloodX

FloodX solves this by treating flood forecasting as a **hyperlocal, time-series intelligence problem combined with graph-based evacuation routing.** It combines multiple advanced paradigms:

* **Time-Series AI:** Processes rolling windows, rates of change, and acceleration of environmental factors.
* **Upstream Awareness:** Configurable propagation delays model how upstream storms become downstream threats.
* **Dynamic Vulnerability:** Factors in exposed demographics (e.g., elderly, children, hospitals) and fluctuating populations.
* **Uncertainty Quantification:** Gracefully degrades predictions when sensors fail or report anomalies, calculating a dynamic confidence score based on data quality, model uncertainty, and signal agreement.
* **Predictive Routing:** Evaluates NetworkX road graphs not just on current risk, but on *future predicted risk* during the evacuation window.
* **Generative AI (Amazon Bedrock):** Translates complex structured ML output into actionable, human-readable, multilingual emergency alerts.
* **Cloud Infrastructure (AWS + MongoDB):** Uses a scalable serverless architecture and specialized time-series storage.

---

## 3. Architecture

```mermaid
flowchart TD
    %% Sensors and Ingestion
    S1[IoT Rain Gauges] --> Gateway
    S2[River Level Sensors] --> Gateway
    S3[Soil Moisture Sensors] --> Gateway
    
    Gateway --> |Time-Series Data| Mongo[MongoDB Atlas\n(Time-Series Collections)]
    Mongo --> API[AWS API Gateway]
    
    %% FloodX Engine (AWS Lambda)
    API --> LambdaRisk[Lambda: Risk Handler]
    API --> LambdaRoute[Lambda: Route Handler]
    API --> LambdaAlert[Lambda: Alert Handler]
    
    %% Internal Pipeline
    subgraph FloodX AI Model Engine
        direction TB
        V[Data Validation & Anomaly Detection] --> FE[Spatiotemporal Feature Engineering]
        FE --> H[Hazard Forecasting\n(Baseline/ML)]
        H --> R[Combined Risk Estimation\n(Hazard x Exposure x Vulnerability)]
        R --> U[Uncertainty & Confidence Estimation]
        R --> F[Multi-Horizon Forecasting\n(15/30/60/120 min)]
        R --> E[Explainability Engine]
    end
    
    LambdaRisk --> FloodX AI Model Engine
    
    %% Routing and Alerting
    FloodX AI Model Engine --> Router[Evacuation Priority\n& Predictive Routing]
    Router --> LambdaRoute
    
    FloodX AI Model Engine --> Bedrock[Amazon Bedrock\n(Generative AI)]
    Bedrock --> LambdaAlert
    
    %% Outputs
    LambdaRisk --> |Risk Snapshots| Mongo
    LambdaRoute --> |Dynamic Routes| Frontend[Dashboard / UI]
    LambdaAlert --> |Multilingual Alerts| Frontend
    LambdaAlert --> |Alerts Log| Mongo
```

---

## 4. AI Components: Distinguishing Rules vs. ML vs. GenAI

In a safety-critical system, it is vital to distinguish between deterministic rules, predictive machine learning, and generative AI. We explicitly separate these layers:

### A. Rules & Statistical Components (Deterministic)
* **Data Validation & Anomaly Detection:** Physical sanity checks (e.g., negative rainfall, impossible sensor jumps).
* **Feature Engineering:** Calculation of explicit time-series features (rolling means, accumulations, derivatives like `river_rise_rate` and `rainfall_acceleration`).
* **Baseline Hazard Engine:** A transparent, geometric-mean-weighted combination of normalized hazard, exposure, and vulnerability scores. Used as a cold-start fallback.
* **Statistical Forecasting:** Linear trend extrapolation of rates and accelerations for 15/30/60/120 minute horizons when ML is unavailable.
* **Evacuation Routing:** Dijkstra's algorithm applied to a composite cost function (`travel_time + α*current_risk + β*future_risk`).

### B. Machine Learning Components
* **Random Forest / XGBoost Hazard Prediction:** Learns non-linear relationships between the spatiotemporal features and the flood-risk labels. Used when `MODEL_MODE="ml"`.
* **Model Uncertainty:** Analyzes the variance across trees in the Random Forest ensemble to contribute to the overall confidence score.

### C. Generative AI (Amazon Bedrock)
* **Contextual Communication:** Amazon Bedrock is used *strictly* as a translation layer. It takes the deterministic/ML risk engine's structured JSON output (e.g., `Risk=CRITICAL, drivers=[river_rise_rate]`) and generates concise, human-readable, multilingual emergency instructions (e.g., Hindi, Gujarati, English).
* **Safety Constraint:** The LLM is **never** allowed to calculate the numerical risk or invent data.

---

## 5. AWS Cloud Infrastructure

FloodX is designed for serverless scalability:
* **API Gateway:** Provides secure REST endpoints for the frontend (`/risk`, `/forecast`, `/route`, `/alert`).
* **AWS Lambda:** Hosts the Python model engine in warm, stateless containers. Adapters parse requests, query recent history from MongoDB, run the FloodX core, and save snapshots.
* **Amazon Bedrock:** Invoked by the Alert Lambda to generate multilingual emergency responses based on structured model payloads.

---

## 6. MongoDB Atlas Data Strategy

MongoDB Atlas acts as the persistent state for the changing world:
* **`sensor_readings`**: Utilizes MongoDB **Time Series Collections** for optimized storage and retrieval of high-frequency IoT data.
* **`risk_snapshots`**: Stores an auditable history of every model prediction, including calculated confidence, explanations, and forecasted horizons.
* **`population_data`**: Stores dynamic vulnerability metrics (e.g., base population + seasonal tourist influxes).
* **`evacuation_graph`**: Maintains the spatial representation of roads, shelters, distances, and base travel times.
* **`alerts_log`**: Audit trail of all Bedrock-generated communications mapped to their triggering risk snapshot.
* **`incident_reports` (Optional):** Stores historical flood events, suitable for future Vector Search (RAG) contextualization.

---

## 7. Limitations & Honesty in AI

As a disaster-intelligence platform, technical transparency is a primary requirement.
* **Synthetic Data:** The current repository utilizes a sophisticated physical-correlation data generator for prototyping and integration testing. **This system has not yet been trained on real historical flood data.** The high performance in demonstrations reflects pipeline correctness, not real-world predictive accuracy.
* **Baseline Calibration:** The baseline risk weights are currently heuristic. Real-world deployment requires rigorous probability calibration against actual historical events.
* **Simplified Graph:** Upstream propagation is currently modeled via a simplified graph. Real implementation requires GIS hydrological modeling.

**Positioning Statement:** *FloodX is a research/prototype decision-support system. It provides AI-assisted risk intelligence for authorized responders. It is not currently authorized to automatically order real-world evacuations.*

---

## 8. Future Roadmap

To transition from a sophisticated prototype to a deployed operational system, the following roadmap is required:

1. **Real Sensor & Dataset Integration:** Connect live data adapters for IMD (India Meteorological Department), ISRO/NRSC satellite precipitation, and Central Water Commission river gauges.
2. **Spatiotemporal GNNs:** Replace the Random Forest hazard model with a Spatiotemporal Graph Neural Network (GNN) that natively understands the topological flow of river networks and road graphs.
3. **Edge Inference:** Compress the ML models (quantization/ONNX) to run on low-power edge gateways (e.g., Raspberry Pi) deployed directly in valleys, ensuring predictions survive internet backhaul failures.
4. **Continual Learning:** Implement automated feedback loops where post-event forensic data (false positives/negatives) systematically retrains the ML models.
5. **RAG Contextualization:** Activate MongoDB Vector Search against a verified database of historical incident reports to provide contextual references ("This exact storm profile occurred in 2013...").
