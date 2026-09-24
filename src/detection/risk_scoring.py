"""Configurable, bounded prioritization indices. Scores are not probabilities."""

import numpy as np


def validate_risk_config(config):
    for key in ("feeder_weights", "meter_weights"):
        weights = config[key]
        if any(value < 0 for value in weights.values()) or not np.isclose(sum(weights.values()), 1):
            raise ValueError(f"{key} must contain nonnegative weights summing to one")
    bands = config["bands"]
    if not 0 < bands["low"] < bands["medium"] < bands["high"] < 1:
        raise ValueError("Risk bands must be ordered in (0, 1)")
    if config["minimum_persistent_days"] < 1:
        raise ValueError("Minimum persistence must be positive")


def risk_label(score, config, data_quality=False):
    if data_quality:
        return "Requires Inspection"
    bands = config["bands"]
    if score >= bands["high"]:
        return "High Risk"
    if score >= bands["medium"]:
        return "Medium Risk"
    if score >= bands["low"]:
        return "Low Risk"
    return "Normal"


def feeder_risk(unexplained_kwh, expected_loss_kwh, baseline_center, baseline_sigma, config):
    excess = max(0.0, unexplained_kwh - baseline_center)
    norm = config["feeder_normalization"]
    sigma = max(baseline_sigma, norm["sigma_floor_fraction"] * expected_loss_kwh, 1e-6)
    z = excess / sigma
    ratio = excess / max(expected_loss_kwh, 1e-6)
    weights = config["feeder_weights"]
    score = np.clip(
        weights["baseline_deviation"] * min(z / norm["z"], 1)
        + weights["excess_to_loss"] * min(ratio / norm["excess_to_loss"], 1), 0, 1
    )
    return float(score), float(z)
