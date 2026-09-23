"""Transparent thresholds and risk categories used in the dashboard."""

import numpy as np


def risk_label(score: float, data_quality: bool = False) -> str:
    if data_quality:
        return "Requires Inspection"
    if score >= 0.78:
        return "High Risk"
    if score >= 0.52:
        return "Medium Risk"
    if score >= 0.25:
        return "Low Risk"
    return "Normal"


def feeder_risk(unexplained_kwh: float, expected_loss_kwh: float, baseline_center: float, baseline_sigma: float) -> tuple[float, float]:
    excess = max(0.0, unexplained_kwh - baseline_center)
    z = excess / max(baseline_sigma, 0.5)
    ratio = max(0.0, unexplained_kwh) / max(expected_loss_kwh, 0.5)
    score = float(np.clip(0.55 * z / 8 + 0.45 * ratio / 3, 0, 1))
    return score, z
