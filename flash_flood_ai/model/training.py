"""
training.py — ML Model Training Pipeline
========================================

Trains a RandomForestClassifier to predict flood hazard using spatiotemporal features.
For the hackathon/prototype, we use the baseline hazard model to generate
synthetic ground-truth labels (Hazard >= 0.55 is dangerous).

IMPORTANT: This pipeline is for validation. A real deployment requires
actual historical flood event data for ground truth.
"""

from __future__ import annotations

import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from model import config
from model.feature_engineering import compute_features, normalize_features
from model.risk_engine import predict_risk, _predict_hazard_baseline


def prepare_dataset(csv_path: str) -> tuple[pd.DataFrame, pd.Series]:
    """Load temporal data, extract features, and generate synthetic labels.
    
    Returns
    -------
    X : pd.DataFrame
        Normalized features (matching config.ML_FEATURE_NAMES).
    y : pd.Series
        Binary classification target (1 if baseline hazard >= 0.55 else 0).
    """
    df = pd.read_csv(csv_path)
    
    # We must process chronologically per location to build rolling features
    df = df.sort_values(by=["id", "timestamp"])
    
    X_rows = []
    y_rows = []
    
    for loc_id, group in df.groupby("id"):
        timeseries = []
        for _, row in group.iterrows():
            obs = row.to_dict()
            timeseries.append(obs)
            
            # Extract features for current step
            features = compute_features(timeseries, upstream_data=None)
            norm_features = normalize_features(features)
            
            # Generate synthetic ground truth using baseline hazard
            baseline_hazard = _predict_hazard_baseline(norm_features)
            is_dangerous = 1 if baseline_hazard >= 0.55 else 0
            
            # Extract ML features in correct order
            x_vec = [norm_features.get(f, 0.0) for f in config.ML_FEATURE_NAMES]
            
            X_rows.append(x_vec)
            y_rows.append(is_dangerous)
            
    X = pd.DataFrame(X_rows, columns=config.ML_FEATURE_NAMES)
    y = pd.Series(y_rows, name="is_dangerous")
    
    # Fill NaN with 0
    X = X.fillna(0.0)
    
    return X, y


def train_model(X: pd.DataFrame, y: pd.Series) -> RandomForestClassifier:
    """Train the RandomForest model."""
    print("Training Random Forest model...")
    clf = RandomForestClassifier(
        n_estimators=config.RF_N_ESTIMATORS,
        max_depth=config.RF_MAX_DEPTH,
        min_samples_leaf=config.RF_MIN_SAMPLES_LEAF,
        random_state=config.RANDOM_SEED,
        n_jobs=-1
    )
    clf.fit(X, y)
    print("Training complete.")
    return clf


def save_model(model: RandomForestClassifier, path: str = config.MODEL_SAVE_PATH) -> None:
    """Save the serialized model to disk."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    joblib.dump(model, path)
    print(f"Model saved to {path}")


if __name__ == "__main__":
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_timeseries.csv")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run generate_sample_data.py first.")
        exit(1)
        
    X, y = prepare_dataset(csv_path)
    print(f"Extracted {len(X)} samples. Target distribution: {y.value_counts().to_dict()}")
    
    model = train_model(X, y)
    save_model(model)
