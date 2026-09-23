"""Approximate balanced three-phase I²R and transformer loss model."""

import numpy as np


def feeder_loss_kwh(load_kwh: np.ndarray, resistance_ohm: float, hours: float, voltage_v: float = 400, power_factor: float = 0.94) -> np.ndarray:
    power_w = load_kwh / hours * 1000
    current_a = power_w / (np.sqrt(3) * voltage_v * power_factor)
    return 3 * current_a**2 * resistance_ohm / 1000 * hours


def transformer_loss_kwh(feeder_input_kwh: np.ndarray, hours: float, core_kw: float, copper_coefficient: float) -> np.ndarray:
    power_kw = feeder_input_kwh / hours
    return (core_kw + copper_coefficient * power_kw**2) * hours
