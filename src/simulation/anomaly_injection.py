"""Scenario injection; ground truth is kept apart from detector inputs."""

import numpy as np
import pandas as pd


def apply_incidents(timestamps: pd.DatetimeIndex, true_kwh: np.ndarray, customers: pd.DataFrame, incidents: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray, pd.DataFrame]:
    reported = true_kwh.copy()
    bypass = np.zeros_like(true_kwh)
    unavailable = np.zeros_like(true_kwh, dtype=bool)
    truth = []
    for incident in incidents:
        j = int(customers.index[customers.customer_id == incident["customer_id"]][0])
        start = timestamps[0] + pd.Timedelta(days=incident["start_day"] - 1)
        end = timestamps[0] + pd.Timedelta(days=incident["end_day"])
        active = (timestamps >= start) & (timestamps < end)
        kind = incident["kind"]
        severity = float(incident["severity"])
        if kind == "under_report":
            reported[active, j] *= 1 - severity
        elif kind == "bypass_load":
            bypass[active, j] = true_kwh[active, j] * severity
        elif kind == "meter_failure":
            reported[active, j] = 0.0
        elif kind == "dropout":
            unavailable[active, j] = True
            reported[active, j] = np.nan
        else:
            raise ValueError(f"Unknown incident: {kind}")
        truth.append({"customer_id": incident["customer_id"], "feeder_id": customers.loc[j, "feeder_id"], "kind": kind, "start": start, "end": end, "severity": severity})
    return reported, bypass, unavailable, pd.DataFrame(truth)
