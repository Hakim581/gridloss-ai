"""Apply synthetic events to physical load and reported meter channels."""

import numpy as np
import pandas as pd


KINDS = {"under_report", "bypass_load", "meter_failure", "dropout", "high_consumption"}


def apply_incidents(timestamps, true_kwh, customers, incidents, baseline_days):
    physical = true_kwh.copy()
    bypass = np.zeros_like(physical)
    unavailable = np.zeros_like(physical, dtype=bool)
    reporting_multiplier = np.ones_like(physical)
    failed = np.zeros_like(physical, dtype=bool)
    truth = []
    for incident in incidents:
        kind = incident["kind"]
        if kind not in KINDS:
            raise ValueError(f"Unknown incident: {kind}")
        if incident["customer_id"] not in set(customers.customer_id):
            raise ValueError("Unknown customer_id")
        j = int(customers.index[customers.customer_id == incident["customer_id"]][0])
        start_day = int(incident["start_day"])
        start_hour = float(incident.get("start_hour", 0))
        duration_days = float(incident.get("duration_days", incident.get("end_day", 0) - start_day + 1))
        severity = float(incident["severity"])
        if start_day <= baseline_days or start_day > len(timestamps) * (timestamps[1] - timestamps[0]) / pd.Timedelta(days=1):
            raise ValueError("Events must start after the clean baseline and within the simulation")
        if not 0 <= start_hour < 24 or duration_days <= 0:
            raise ValueError("Invalid event start hour or duration")
        if kind == "under_report" and not 0 <= severity <= 1:
            raise ValueError("Under-reporting severity must be between 0 and 1")
        if severity < 0:
            raise ValueError("Severity must be nonnegative")
        start = timestamps[0] + pd.Timedelta(days=start_day - 1, hours=start_hour)
        end = min(start + pd.Timedelta(days=duration_days), timestamps[-1] + (timestamps[1] - timestamps[0]))
        active = np.asarray((timestamps >= start) & (timestamps < end))
        if kind == "high_consumption":
            physical[active, j] *= 1 + severity
        elif kind == "under_report":
            reporting_multiplier[active, j] *= 1 - severity
        elif kind == "bypass_load":
            bypass[active, j] += physical[active, j] * severity
        elif kind == "meter_failure":
            failed[active, j] = True
        elif kind == "dropout":
            unavailable[active, j] = True
        truth.append({"customer_id": incident["customer_id"], "feeder_id": customers.loc[j, "feeder_id"],
                      "kind": kind, "start": start, "end": end, "severity": severity})
    return physical, bypass, unavailable, reporting_multiplier, failed, pd.DataFrame(
        truth, columns=["customer_id", "feeder_id", "kind", "start", "end", "severity"]
    )
