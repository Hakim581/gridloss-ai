"""Feeder localization and cautious meter inspection priority."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .anomaly_model import score_meter_anomalies
from .energy_balance import daily_balances, interval_balances
from .feature_engineering import meter_daily_features
from .risk_scoring import feeder_risk, risk_label, validate_risk_config


@dataclass
class DetectionResult:
    interval: pd.DataFrame
    transformer: pd.DataFrame
    feeder_daily: pd.DataFrame
    meter_daily: pd.DataFrame
    feeder_summary: pd.DataFrame
    meter_summary: pd.DataFrame


def detect(simulation):
    risk_cfg = simulation.config["risk_scoring"]
    validate_risk_config(risk_cfg)
    interval, transformer = interval_balances(simulation)
    feeder_daily = daily_balances(interval)
    baseline_days = simulation.config["simulation"]["baseline_days"]
    baseline_end = feeder_daily.date.min() + pd.Timedelta(days=baseline_days)
    baseline = feeder_daily[feeder_daily.date < baseline_end]
    stats = baseline.groupby("feeder_id").unexplained_kwh.agg(
        baseline_center="median", baseline_sigma="std"
    )
    feeder_daily = feeder_daily.join(stats, on="feeder_id")
    risks = [feeder_risk(
        row.unexplained_kwh, row.expected_technical_loss_kwh,
        row.baseline_center, row.baseline_sigma, risk_cfg
    ) for row in feeder_daily.itertuples()]
    feeder_daily["risk_score"] = [value[0] for value in risks]
    feeder_daily["residual_z"] = [value[1] for value in risks]
    feeder_daily["loss_ratio"] = (
        (feeder_daily.unexplained_kwh - feeder_daily.baseline_center).clip(lower=0)
        / feeder_daily.expected_technical_loss_kwh.clip(lower=1e-6)
    )
    intervals_per_day = round(24 * 60 / simulation.config["simulation"]["interval_minutes"])
    feeder_daily["data_quality_issue"] = (
        feeder_daily.missing_meter_intervals / (10 * intervals_per_day)
        >= risk_cfg["missing_day_exclusion_fraction"]
    )
    feeder_daily["candidate_alert"] = (
        (feeder_daily.date >= baseline_end)
        & ~feeder_daily.data_quality_issue
        & (feeder_daily.risk_score >= risk_cfg["bands"]["medium"])
    )
    feeder_daily = feeder_daily.sort_values(["feeder_id", "date"]).reset_index(drop=True)
    persistence = risk_cfg["minimum_persistent_days"]
    feeder_daily["qualifying_alert"] = feeder_daily.groupby("feeder_id").candidate_alert.transform(
        lambda series: series.rolling(persistence, min_periods=persistence).sum().eq(persistence)
    )
    feeder_daily["risk_label"] = [
        risk_label(row.risk_score, risk_cfg) if row.qualifying_alert else
        ("Data Quality Issue" if row.data_quality_issue else
         risk_label(min(row.risk_score, risk_cfg["bands"]["medium"] - 1e-6), risk_cfg))
        for row in feeder_daily.itertuples()
    ]

    meter_daily = score_meter_anomalies(
        meter_daily_features(simulation), baseline_days,
        simulation.config["simulation"]["seed"], risk_cfg
    )
    meter_daily = meter_daily.merge(
        feeder_daily[["date", "feeder_id", "risk_score", "qualifying_alert", "unexplained_kwh"]],
        on=["date", "feeder_id"], validate="many_to_one"
    )
    weights = risk_cfg["meter_weights"]
    meter_daily["inspection_score"] = np.clip(
        weights["consumption_drop"] * meter_daily.consumption_drop
        + weights["behavioral_anomaly"] * meter_daily.ml_anomaly_score
        + weights["feeder_context"] * meter_daily.risk_score * meter_daily.qualifying_alert,
        0, 1
    )
    meter_daily.loc[meter_daily.missing_fraction >= 0.5, "inspection_score"] = 0
    meter_daily["health_issue"] = (
        (meter_daily.missing_fraction >= 0.5) | (meter_daily.zero_fraction >= 0.8)
    )
    meter_daily["risk_label"] = [
        risk_label(row.inspection_score, risk_cfg, row.health_issue)
        for row in meter_daily.itertuples()
    ]
    meter_daily["explanation"] = meter_daily.apply(_meter_explanation, axis=1)

    after = feeder_daily[feeder_daily.date >= baseline_end]
    summary_rows = []
    for feeder, group in after.groupby("feeder_id"):
        qualified = group[group.qualifying_alert]
        onset = qualified.date.min() if len(qualified) else pd.NaT
        peak = group.loc[group.unexplained_kwh.idxmax()]
        top_risk = float(qualified.risk_score.max()) if len(qualified) else float(
            min(group.risk_score.max(), risk_cfg["bands"]["medium"] - 1e-6)
        )
        summary_rows.append({
            "feeder_id": feeder, "risk_score": top_risk,
            "risk_label": risk_label(top_risk, risk_cfg),
            "unexplained_kwh": float(group.unexplained_kwh.clip(lower=0).sum()),
            "peak_daily_unexplained_kwh": float(peak.unexplained_kwh),
            "peak_loss_ratio": float(peak.loss_ratio),
            "onset": onset, "data_quality_intervals": int(group.missing_meter_intervals.sum()),
            "explanation": _feeder_explanation(feeder, peak, onset),
        })
    feeder_summary = pd.DataFrame(summary_rows).sort_values("risk_score", ascending=False)
    meter_after = meter_daily[meter_daily.date >= baseline_end]
    meter_rows = []
    for customer, group in meter_after.groupby("customer_id"):
        worst = group.loc[group.inspection_score.idxmax()]
        health = group[group.health_issue]
        notable = group[(group.inspection_score >= risk_cfg["bands"]["medium"]) | group.health_issue]
        evidence = group.loc[notable.index[0]] if len(notable) else worst
        meter_rows.append({
            "customer_id": customer, "feeder_id": worst.feeder_id,
            "inspection_score": float(worst.inspection_score),
            "risk_label": risk_label(float(worst.inspection_score), risk_cfg, bool(len(health))),
            "onset": notable.date.min() if len(notable) else pd.NaT,
            "explanation": _meter_explanation(evidence),
        })
    meter_summary = pd.DataFrame(meter_rows)
    meter_summary["_priority"] = meter_summary.risk_label.map({
        "High Risk": 0, "Medium Risk": 1, "Requires Inspection": 2,
        "Low Risk": 3, "Normal": 4
    })
    meter_summary = meter_summary.sort_values(
        ["_priority", "inspection_score"], ascending=[True, False]
    ).drop(columns="_priority")
    return DetectionResult(interval, transformer, feeder_daily, meter_daily,
                           feeder_summary, meter_summary)


def _meter_explanation(row):
    if row.missing_fraction >= 0.5:
        return "Rabitə məlumatı çatışmır; fiziki itki və ya sui-istifadə üçün kifayət qədər sübut yoxdur."
    if row.zero_fraction >= 0.8:
        return "Sayğac uzun müddət sıfır göstərir; sayğac sağlamlığı yoxlanmalıdır, səbəb təsdiqlənməyib."
    if row.consumption_drop >= 0.15 and row.qualifying_alert:
        return (f"Qeyd edilən enerji sağlam bazanın {row.consumption_ratio:.0%}-i qədərdir; "
                f"eyni vaxtda {row.feeder_id} enerji balansında davamlı fərq var. Yoxlama prioritetidir.")
    if row.consumption_drop >= 0.15:
        return "Sayğac davranışı bazadan aşağıdır; fider səviyyəsində təsdiqlənmiş itki yoxdur."
    if row.qualifying_alert:
        return "Fiderdə izah olunmayan enerji var; bu sayğacda ayrıca sübut yoxdur. Müştəriyə aid edilmir."
    return "Sayğac məlumatı sağlam baza diapazonundadır."


def _feeder_explanation(feeder, peak, onset):
    if pd.isna(onset):
        return f"{feeder}: davamlı fiziki itki siqnalı yoxdur; ölçmə və model variasiyası izlənir."
    return (f"{feeder}: gündəlik izah olunmayan enerji zirvədə {peak.unexplained_kwh:.1f} kWh; "
            f"baza mərkəzindən {peak.residual_z:.1f} standart sapma yüksəkdir. "
            f"İlk davamlı siqnal: {onset.date()}. Fider sübutu tək müştərini müəyyən etmir.")

