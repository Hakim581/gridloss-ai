"""Isolation Forest on daily meter behavior, calibrated to baseline scores."""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def score_meter_anomalies(features: pd.DataFrame, baseline_days: int, seed: int) -> pd.DataFrame:
    result = features.copy()
    cols = ["consumption_ratio", "zero_fraction", "missing_fraction"]
    data = result[cols].replace([np.inf, -np.inf], np.nan).fillna({"consumption_ratio": 1.0, "zero_fraction": 0.0, "missing_fraction": 0.0})
    baseline = result.date < result.date.min() + pd.Timedelta(days=baseline_days)
    model = IsolationForest(n_estimators=120, max_samples=min(256, int(baseline.sum())), contamination=0.05, random_state=seed)
    model.fit(data.loc[baseline])
    raw = -model.score_samples(data)
    threshold = float(np.quantile(raw[baseline], 0.99))
    result["ml_anomaly_score"] = np.clip((raw - threshold) / 0.12, 0, 1)
    result["ml_outlier"] = raw > threshold
    return result
