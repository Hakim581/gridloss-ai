"""Isolation Forest behavioral score calibrated on clean baseline samples."""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def score_meter_anomalies(features, baseline_days, seed, config):
    result = features.copy()
    cols = ["consumption_ratio", "zero_fraction", "missing_fraction"]
    data = result[cols].replace([np.inf, -np.inf], np.nan).fillna(
        {"consumption_ratio": 1.0, "zero_fraction": 0.0, "missing_fraction": 0.0}
    )
    baseline = result.date < result.date.min() + pd.Timedelta(days=baseline_days)
    model = IsolationForest(
        n_estimators=120, max_samples=min(256, int(baseline.sum())),
        contamination=config["ml_contamination"], random_state=seed,
    )
    model.fit(data.loc[baseline])
    raw = -model.score_samples(data)
    threshold = float(np.quantile(raw[baseline.to_numpy()], config["ml_baseline_quantile"]))
    result["ml_anomaly_score"] = np.clip(
        (raw - threshold) / config["ml_score_scale"], 0, 1
    )
    result["ml_outlier"] = raw > threshold
    return result

