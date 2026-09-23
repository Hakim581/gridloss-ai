"""Feeder localization and cautious meter inspection ranking."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .anomaly_model import score_meter_anomalies
from .energy_balance import daily_balances, interval_balances
from .feature_engineering import meter_daily_features
from .risk_scoring import feeder_risk, risk_label


@dataclass
class DetectionResult:
    interval: pd.DataFrame
    transformer: pd.DataFrame
    feeder_daily: pd.DataFrame
    meter_daily: pd.DataFrame
    feeder_summary: pd.DataFrame
    meter_summary: pd.DataFrame


def detect(simulation) -> DetectionResult:
    interval, transformer = interval_balances(simulation)
    feeder_daily = daily_balances(interval)
    baseline_days = simulation.config["simulation"]["baseline_days"]
    baseline_end = feeder_daily.date.min() + pd.Timedelta(days=baseline_days)
    baseline = feeder_daily[feeder_daily.date < baseline_end]
    stats = baseline.groupby("feeder_id").unexplained_kwh.agg(["median", "std"]).rename(columns={"median": "baseline_center", "std": "baseline_sigma"})
    feeder_daily = feeder_daily.join(stats, on="feeder_id")
    risks = [feeder_risk(r.unexplained_kwh, r.expected_technical_loss_kwh, r.baseline_center, r.baseline_sigma) for r in feeder_daily.itertuples()]
    feeder_daily["risk_score"] = [x[0] for x in risks]
    feeder_daily["residual_z"] = [x[1] for x in risks]
    feeder_daily["risk_label"] = feeder_daily.risk_score.map(risk_label)
    feeder_daily["loss_ratio"] = feeder_daily.unexplained_kwh.clip(lower=0) / feeder_daily.expected_technical_loss_kwh.clip(lower=0.5)

    meter_daily = score_meter_anomalies(meter_daily_features(simulation), baseline_days, simulation.config["simulation"]["seed"])
    meter_daily = meter_daily.merge(feeder_daily[["date", "feeder_id", "risk_score", "unexplained_kwh"]], on=["date", "feeder_id"], validate="many_to_one")
    # A feeder imbalance is evidence for the feeder, not proof about any one meter.
    meter_daily["inspection_score"] = np.clip(0.62 * meter_daily.consumption_drop + 0.18 * meter_daily.ml_anomaly_score + 0.20 * meter_daily.risk_score, 0, 1)
    meter_daily.loc[meter_daily.missing_fraction >= 0.5, "inspection_score"] = 0.0
    meter_daily["risk_label"] = [risk_label(r.inspection_score, r.missing_fraction >= 0.5 or r.zero_fraction >= 0.8) for r in meter_daily.itertuples()]
    meter_daily["explanation"] = meter_daily.apply(_meter_explanation, axis=1)

    after = feeder_daily[feeder_daily.date >= baseline_end]
    summary_rows = []
    for feeder, group in after.groupby("feeder_id"):
        abnormal = group[group.risk_score >= 0.52]
        peak = group.loc[group.unexplained_kwh.idxmax()]
        top_risk = float(group.risk_score.max())
        implicated = meter_daily[(meter_daily.feeder_id == feeder) & (meter_daily.date >= baseline_end) & (meter_daily.consumption_drop >= 0.3)].customer_id.unique().tolist()
        onset = abnormal.date.min() if len(abnormal) else pd.NaT
        summary_rows.append({
            "feeder_id": feeder, "risk_score": top_risk, "risk_label": risk_label(top_risk),
            "unexplained_kwh": float(group.unexplained_kwh.clip(lower=0).sum()),
            "peak_daily_unexplained_kwh": float(peak.unexplained_kwh), "peak_loss_ratio": float(peak.loss_ratio),
            "onset": onset, "data_quality_intervals": int(group.missing_meter_intervals.sum()),
            "explanation": _feeder_explanation(feeder, peak, onset, implicated),
        })
    feeder_summary = pd.DataFrame(summary_rows).sort_values("risk_score", ascending=False)
    meter_after = meter_daily[meter_daily.date >= baseline_end]
    meter_summary_rows = []
    for customer, group in meter_after.groupby("customer_id"):
        worst = group.loc[group.inspection_score.idxmax()]
        quality = bool((group.missing_fraction >= 0.5).any() or (group.zero_fraction >= 0.8).any())
        score = float(worst.inspection_score)
        label = risk_label(score, quality)
        notable = group[(group.inspection_score >= 0.52) | (group.missing_fraction >= 0.5) | (group.zero_fraction >= 0.8)]
        meter_summary_rows.append({
            "customer_id": customer, "feeder_id": worst.feeder_id, "inspection_score": score,
            "risk_label": label, "onset": notable.date.min() if len(notable) else pd.NaT,
            "explanation": _meter_explanation(group.loc[notable.index[0]]) if len(notable) else _meter_explanation(worst),
        })
    meter_summary = pd.DataFrame(meter_summary_rows)
    meter_summary["_priority"] = meter_summary.risk_label.map({"Requires Inspection": 0, "High Risk": 1, "Medium Risk": 2, "Low Risk": 3, "Normal": 4})
    meter_summary = meter_summary.sort_values(["_priority", "inspection_score"], ascending=[True, False]).drop(columns="_priority")
    return DetectionResult(interval, transformer, feeder_daily, meter_daily, feeder_summary, meter_summary)


def _meter_explanation(row) -> str:
    if row.missing_fraction >= 0.5:
        return "Communication data are missing; check telemetry before interpreting the energy balance."
    if row.zero_fraction >= 0.8:
        return "Meter reports zero through most intervals while feeder energy remains measured; meter inspection recommended."
    if row.consumption_drop >= 0.3:
        return f"Reported daily energy is {row.consumption_ratio:.0%} of its clean baseline; verify meter and customer context."
    if row.risk_score >= 0.52:
        return "Feeder has unexplained energy, but this meter has no distinct anomaly; no individual attribution."
    return "Reported consumption is within the observed baseline range."


def _feeder_explanation(feeder: str, peak, onset, implicated: list[str]) -> str:
    if pd.isna(onset):
        return f"{feeder} has no sustained elevated unexplained energy after the baseline period."
    meters = f" Anomalous meter patterns: {', '.join(implicated)}." if implicated else " No individual meter can be isolated from this evidence."
    return (f"{feeder}: peak daily unexplained energy {peak.unexplained_kwh:.1f} kWh "
            f"({peak.loss_ratio:.1f}× expected technical loss); anomaly begins {onset.date()}." + meters)
