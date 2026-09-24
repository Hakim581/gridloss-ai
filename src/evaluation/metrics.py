"""Executed synthetic validation; truth is used here only after detection."""

from copy import deepcopy

import numpy as np
import pandas as pd

from src.detection.localization import detect
from src.simulation.simulator import load_config, simulate


PHYSICAL_EVENTS = {"under_report", "bypass_load", "meter_failure"}


def _rate(numerator, denominator):
    return float(numerator / denominator) if denominator else 0.0


def evaluate(simulation, result):
    """Feeder-day binary metrics after baseline; FPR denominator is true negative feeder-days."""
    start = result.feeder_daily.date.min() + pd.Timedelta(
        days=simulation.config["simulation"]["baseline_days"]
    )
    daily = result.feeder_daily[result.feeder_daily.date >= start]
    actual = set()
    for event in simulation.truth.itertuples():
        if event.kind not in PHYSICAL_EVENTS:
            continue
        dates = pd.date_range(event.start.floor("D"), (event.end - pd.Timedelta(nanoseconds=1)).floor("D"), freq="D")
        actual.update((event.feeder_id, date) for date in dates if date >= start)
    universe = set(zip(daily.feeder_id, daily.date))
    predicted = set(zip(
        daily.loc[daily.qualifying_alert, "feeder_id"],
        daily.loc[daily.qualifying_alert, "date"],
    ))
    tp = len(actual & predicted)
    fp = len(predicted - actual)
    fn = len(actual - predicted)
    tn = len(universe - actual - predicted)
    precision, recall = _rate(tp, tp + fp), _rate(tp, tp + fn)
    event_rows = []
    for event in simulation.truth.itertuples():
        if event.kind not in PHYSICAL_EVENTS:
            continue
        window = daily[(daily.date >= event.start.floor("D"))
                       & (daily.date < event.end)]
        alerts = window[(window.feeder_id == event.feeder_id) & window.qualifying_alert]
        detected = len(alerts) > 0
        first_available = alerts.date.iloc[0] + pd.Timedelta(days=1) if detected else pd.NaT
        highest = window.groupby("feeder_id").risk_score.max()
        located = bool(detected and highest.idxmax() == event.feeder_id)
        delay = (first_available - event.start) / pd.Timedelta(hours=1) if detected else np.nan
        top3 = result.meter_summary.head(3).customer_id.tolist()
        event_rows.append({
            "kind": event.kind, "severity": event.severity, "detected": detected,
            "localized": located, "delay_hours": delay,
            "top3_customer": event.customer_id in top3 if event.kind == "under_report" else np.nan,
        })
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall,
        "f1": _rate(2 * precision * recall, precision + recall),
        "false_positive_rate": _rate(fp, fp + tn),
        "feeder_localization_accuracy": _rate(
            sum(row["localized"] for row in event_rows), len(event_rows)
        ),
        "average_detection_delay_hours": float(np.nanmean(
            [row["delay_hours"] for row in event_rows]
        )) if any(row["detected"] for row in event_rows) else np.nan,
        "detected_events": sum(row["detected"] for row in event_rows),
        "undetected_events": sum(not row["detected"] for row in event_rows),
        "event_rows": event_rows,
    }


def scenario_catalog(config):
    evaluation = config["evaluation"]
    start = evaluation["event_start_day"]
    duration = evaluation["event_duration_days"]
    base = {"customer_id": "M17", "start_day": start, "duration_days": duration}
    scenarios = [("Clean network", [])]
    scenarios += [
        (f"Under-report {round(severity * 100)}%", [{
            **base, "kind": "under_report", "severity": severity,
        }]) for severity in evaluation["under_report_severities"]
    ]
    scenarios += [
        ("Unmetered load", [{**base, "customer_id": "M19", "kind": "bypass_load", "severity": 0.8}]),
        ("Meter failure", [{**base, "customer_id": "M05", "kind": "meter_failure", "severity": 1.0}]),
        ("Communication dropout", [{**base, "customer_id": "M05", "kind": "dropout", "severity": 1.0}]),
        ("Legitimate high consumption", [{**base, "kind": "high_consumption", "severity": 1.0}]),
    ]
    return scenarios


def evaluate_suite(seeds=None, config=None, scenario_names=None):
    """Run every named scenario for every seed; never called on ordinary app reruns."""
    config = load_config() if config is None else config
    seeds = list(config["evaluation"]["seeds"] if seeds is None else seeds)
    scenarios = scenario_catalog(config)
    if scenario_names is not None:
        scenarios = [(name, incidents) for name, incidents in scenarios if name in scenario_names]
    rows = []
    for seed in seeds:
        for name, incidents in scenarios:
            run_config = deepcopy(config)
            run_config["simulation"]["seed"] = int(seed)
            run_config["incidents"] = incidents
            simulation = simulate(run_config)
            result = evaluate(simulation, detect(simulation))
            event = result["event_rows"][0] if result["event_rows"] else None
            rows.append({
                "seed": seed, "scenario": name, "tp": result["tp"], "fp": result["fp"],
                "fn": result["fn"], "tn": result["tn"],
                "detected": event["detected"] if event else False,
                "localized": event["localized"] if event else np.nan,
                "delay_hours": event["delay_hours"] if event else np.nan,
                "top3_customer": event["top3_customer"] if event else np.nan,
            })
    runs = pd.DataFrame(rows)
    tp, fp, fn, tn = (int(runs[col].sum()) for col in ("tp", "fp", "fn", "tn"))
    precision, recall = _rate(tp, tp + fp), _rate(tp, tp + fn)
    physical = runs[runs.scenario.isin(
        ["Under-report 10%", "Under-report 20%", "Under-report 30%",
         "Under-report 40%", "Unmetered load", "Meter failure"]
    )]
    summary = {
        "precision": precision, "recall": recall,
        "f1": _rate(2 * precision * recall, precision + recall),
        "false_positive_rate": _rate(fp, fp + tn),
        "feeder_localization_accuracy": float(physical.localized.mean()),
        "average_detection_delay_hours": float(physical.delay_hours.mean()),
        "detected_events": int(physical.detected.sum()),
        "undetected_events": int((~physical.detected).sum()),
        "scenarios": len(runs), "seeds": len(seeds),
        "clean_controls": int((runs.scenario == "Clean network").sum()),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }
    by_scenario = runs.groupby("scenario", sort=False).agg(
        runs=("seed", "size"), detection_rate=("detected", "mean"),
        localization_accuracy=("localized", "mean"),
        average_delay_hours=("delay_hours", "mean"),
        top3_customer_rate=("top3_customer", "mean"),
        false_positive_feeder_days=("fp", "sum"),
    ).reset_index()
    return summary, by_scenario, runs
