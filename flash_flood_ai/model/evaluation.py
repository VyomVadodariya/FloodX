"""
evaluation.py — ML Model Evaluation and Temporal Validation
===========================================================

Evaluates the RandomForest model using temporal train/test splitting
to prevent future data leakage. Computes rigorous classification metrics
including Precision, Recall, ROC-AUC, PR-AUC, and False Negative analysis
for safety-critical high-hazard events.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix
)
from sklearn.calibration import calibration_curve

from model.training import prepare_dataset, train_model

def temporal_split(X: pd.DataFrame, y: pd.Series, split_ratio: float = 0.8) -> tuple:
    """Split data temporally without shuffling to prevent data leakage."""
    split_idx = int(len(X) * split_ratio)
    
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    return X_train, X_test, y_train, y_test


def evaluate_model(clf, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    """Compute rigorous safety-critical evaluation metrics."""
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    
    try:
        roc_auc = roc_auc_score(y_test, y_prob)
        pr_auc = average_precision_score(y_test, y_prob)
    except ValueError:
        roc_auc = 0.0
        pr_auc = 0.0
        
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel() if len(cm.ravel()) == 4 else (0, 0, 0, 0)
    
    # Calibration
    prob_true, prob_pred = calibration_curve(y_test, y_prob, n_bins=10)
    
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "confusion_matrix": {"TN": int(tn), "FP": int(fp), "FN": int(fn), "TP": int(tp)},
        "false_negative_rate": round(fn / max((fn + tp), 1), 4)
    }

def print_evaluation_report(metrics: dict):
    """Print a human-readable evaluation report."""
    print("\n--- FloodX ML Evaluation Report ---")
    print(f"Precision (PPV): {metrics['precision']:.4f}")
    print(f"Recall (Sensitivity): {metrics['recall']:.4f}")
    print(f"F1 Score: {metrics['f1']:.4f}")
    print(f"ROC-AUC: {metrics['roc_auc']:.4f}")
    print(f"PR-AUC: {metrics['pr_auc']:.4f}")
    print("\nConfusion Matrix:")
    print(f"  True Negatives:  {metrics['confusion_matrix']['TN']}")
    print(f"  False Positives: {metrics['confusion_matrix']['FP']} (False Alarms)")
    print(f"  False Negatives: {metrics['confusion_matrix']['FN']} (MISSED HAZARDS - CRITICAL!)")
    print(f"  True Positives:  {metrics['confusion_matrix']['TP']}")
    print(f"\nFalse Negative Rate: {metrics['false_negative_rate']:.2%}")
    if metrics['false_negative_rate'] > 0.05:
        print("WARNING: False Negative Rate is high. Model may miss dangerous events.")
    else:
        print("SAFETY CHECK: False Negative Rate is acceptable (< 5%).")


if __name__ == "__main__":
    import os
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_timeseries.csv")
    print("Preparing dataset with temporal features...")
    X, y = prepare_dataset(csv_path)
    
    if len(y.unique()) < 2:
        print("Error: Dataset requires both safe and hazardous events to evaluate.")
        exit(1)
        
    print("\nPerforming temporal train/test split...")
    X_train, X_test, y_train, y_test = temporal_split(X, y)
    
    clf = train_model(X_train, y_train)
    
    print("\nEvaluating model on unseen temporal future...")
    metrics = evaluate_model(clf, X_test, y_test)
    print_evaluation_report(metrics)
