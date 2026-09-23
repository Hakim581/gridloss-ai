"""Compare alerts against synthetic ground truth, never used for scoring."""

import pandas as pd


def evaluate(simulation, result) -> dict[str, float]:
    daily = result.feeder_daily.copy()
    truth = simulation.truth[simulation.truth.kind != "dropout"]
    actual = set()
    for row in truth.itertuples():
        for date in pd.date_range(row.start, row.end - pd.Timedelta(days=1), freq="D"):
            actual.add((row.feeder_id, date))
    predicted = set(zip(daily.loc[daily.risk_score >= 0.52, "feeder_id"], daily.loc[daily.risk_score >= 0.52, "date"]))
    tp = len(actual & predicted)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(actual) if actual else 0.0
    all_cases = set(zip(daily.feeder_id, daily.date))
    false_positive = len(predicted - actual)
    return {
        "feeder_day_precision": precision,
        "feeder_day_recall": recall,
        "feeder_day_false_positives": float(false_positive),
        "evaluated_feeder_days": float(len(all_cases)),
    }
