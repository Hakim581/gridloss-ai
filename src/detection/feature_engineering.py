"""Interpretable daily meter behavior relative to a clean pre-event reference."""

import numpy as np
import pandas as pd


def meter_daily_features(simulation):
    meters = simulation.meters.copy()
    meters["date"] = meters.timestamp.dt.floor("D")
    meters["is_zero"] = meters.reported_kwh.fillna(-1).eq(0)
    daily = meters.groupby(["date", "customer_id", "feeder_id"], as_index=False).agg(
        reported_kwh=("reported_kwh", "sum"),
        missing_fraction=("reported_kwh", lambda x: x.isna().mean()),
        zero_fraction=("is_zero", "mean"),
    )
    daily.loc[daily.missing_fraction.eq(1), "reported_kwh"] = np.nan
    daily["is_weekend"] = daily.date.dt.dayofweek >= 5
    baseline_end = daily.date.min() + pd.Timedelta(days=simulation.config["simulation"]["baseline_days"])
    reference = daily[daily.date < baseline_end].groupby(
        ["customer_id", "is_weekend"]
    ).reported_kwh.median().rename("reference_kwh")
    daily = daily.join(reference, on=["customer_id", "is_weekend"])
    daily["consumption_ratio"] = daily.reported_kwh / daily.reference_kwh
    risk_cfg = simulation.config["risk_scoring"]
    start = risk_cfg["meter_drop_start_ratio"]
    full = risk_cfg["meter_drop_full_ratio"]
    daily["consumption_drop"] = np.clip(
        (start - daily.consumption_ratio) / (start - full), 0, 1
    ).fillna(0)
    return daily

