"""Daily meter features; training references only use the clean baseline window."""

import numpy as np
import pandas as pd


def meter_daily_features(simulation) -> pd.DataFrame:
    meters = simulation.meters.copy()
    meters["date"] = meters.timestamp.dt.floor("D")
    meters["is_zero"] = meters.reported_kwh.fillna(-1).eq(0)
    daily = meters.groupby(["date", "customer_id", "feeder_id"], as_index=False).agg(
        reported_kwh=("reported_kwh", "sum"), missing_fraction=("reported_kwh", lambda x: x.isna().mean()),
        zero_fraction=("is_zero", "mean"),
    )
    daily.loc[daily.missing_fraction.eq(1), "reported_kwh"] = np.nan
    start = daily.date.min()
    daily["is_weekend"] = daily.date.dt.dayofweek >= 5
    baseline = daily[daily.date < start + pd.Timedelta(days=simulation.config["simulation"]["baseline_days"])]
    reference = baseline.groupby(["customer_id", "is_weekend"]).reported_kwh.median().rename("reference_kwh")
    daily = daily.join(reference, on=["customer_id", "is_weekend"])
    daily["consumption_ratio"] = daily.reported_kwh / daily.reference_kwh
    daily["consumption_drop"] = np.clip((0.88 - daily.consumption_ratio) / 0.78, 0, 1).fillna(0)
    return daily
