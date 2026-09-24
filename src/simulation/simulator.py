"""Reproducible physical state and separate noisy measured channels."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .anomaly_injection import apply_incidents
from .customer_profiles import consumption_matrix
from .network import build_network
from .technical_losses import feeder_loss_kwh, transformer_loss_kwh


@dataclass
class Simulation:
    customers: pd.DataFrame
    meters: pd.DataFrame  # detector-visible reported readings only
    feeders: pd.DataFrame  # detector-visible measured input
    transformer: pd.DataFrame  # detector-visible measured input
    truth: pd.DataFrame  # evaluation only; never read by detect()
    config: dict
    physical_meters: pd.DataFrame
    physical_feeders: pd.DataFrame
    physical_transformer: pd.DataFrame


def load_config(path: str | Path = "config/config.yaml") -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def simulate(config: dict | None = None) -> Simulation:
    config = load_config() if config is None else config
    cfg = config["simulation"]
    truth_cfg = config["network_truth"]
    noise_cfg = config["measurement_uncertainty"]
    hours = cfg["interval_minutes"] / 60
    periods = cfg["days"] * round(24 / hours)
    stamps = pd.date_range(cfg["start"], periods=periods, freq=f"{cfg['interval_minutes']}min")
    customers = build_network()
    base = consumption_matrix(stamps, customers, cfg["seed"])
    physical, bypass, unavailable, multiplier, failed, truth = apply_incidents(
        stamps, base, customers, config.get("incidents", [config["default_demo"]]), cfg["baseline_days"]
    )
    rng = np.random.default_rng(cfg["seed"] + 100_003)
    decimals = int(noise_cfg["energy_rounding_decimals"])
    measured_customer = np.maximum(0, physical * (1 + rng.normal(
        0, noise_cfg["customer_meter_relative_std"], physical.shape
    )))
    reported = np.round(measured_customer * multiplier, decimals)
    reported[failed] = 0
    reported[unavailable] = np.nan
    meter_keys = {
        "timestamp": np.repeat(stamps.to_numpy(), len(customers)),
        "customer_id": np.tile(customers.customer_id.to_numpy(), len(stamps)),
        "feeder_id": np.tile(customers.feeder_id.to_numpy(), len(stamps)),
    }
    meters = pd.DataFrame({**meter_keys, "reported_kwh": reported.ravel(),
                           "quality": np.where(unavailable.ravel(), "missing", "ok")})
    physical_meters = pd.DataFrame({**meter_keys, "true_customer_kwh": physical.ravel(),
                                    "true_unmetered_kwh": bypass.ravel()})
    day_index = np.arange(periods) * hours / 24
    temperature = (truth_cfg["conductor_temperature_c"]
                   + truth_cfg["daily_temperature_swing_c"] * np.sin(2 * np.pi * day_index / 7))
    voltage = truth_cfg["voltage_v"] * (1 + truth_cfg["voltage_daily_variation_fraction"]
                                       * np.sin(2 * np.pi * day_index))
    pf = truth_cfg["power_factor"] + truth_cfg["power_factor_daily_variation"] * np.sin(
        2 * np.pi * day_index / 3
    )
    measured_feeders = []
    physical_feeders = []
    true_inputs = []
    for feeder in ("F1", "F2", "F3"):
        mask = customers.feeder_id.to_numpy() == feeder
        delivered = physical[:, mask].sum(axis=1)
        unmetered = bypass[:, mask].sum(axis=1)
        resistance = truth_cfg["feeder_resistance_ohm"][feeder] * (
            1 + truth_cfg["resistance_temperature_coefficient_per_c"]
            * (temperature - truth_cfg["resistance_reference_c"])
        )
        actual_loss = feeder_loss_kwh(delivered + unmetered, resistance, hours, voltage, pf)
        true_input = delivered + unmetered + actual_loss
        measured_input = np.round(np.maximum(0, true_input * (1 + rng.normal(
            0, noise_cfg["feeder_meter_relative_std"], periods
        ))), decimals)
        measured_feeders.append(pd.DataFrame({"timestamp": stamps, "feeder_id": feeder,
                                               "input_kwh": measured_input}))
        physical_feeders.append(pd.DataFrame({
            "timestamp": stamps, "feeder_id": feeder, "true_customer_kwh": delivered,
            "true_unmetered_kwh": unmetered, "true_technical_loss_kwh": actual_loss,
            "true_input_kwh": true_input,
        }))
        true_inputs.append(true_input)
    feeders = pd.concat(measured_feeders, ignore_index=True)
    physical_feeder_frame = pd.concat(physical_feeders, ignore_index=True)
    total_true_feeder = np.sum(true_inputs, axis=0)
    true_transformer_loss = transformer_loss_kwh(
        total_true_feeder, hours, truth_cfg["transformer_core_loss_kw"],
        truth_cfg["transformer_copper_coefficient"]
    )
    true_transformer_input = total_true_feeder + true_transformer_loss
    transformer = pd.DataFrame({
        "timestamp": stamps,
        "input_kwh": np.round(np.maximum(0, true_transformer_input * (1 + rng.normal(
            0, noise_cfg["transformer_meter_relative_std"], periods
        ))), decimals),
    })
    physical_transformer = pd.DataFrame({
        "timestamp": stamps, "true_feeder_inputs_kwh": total_true_feeder,
        "true_technical_loss_kwh": true_transformer_loss,
        "true_input_kwh": true_transformer_input,
    })
    return Simulation(customers, meters, feeders, transformer, truth, config,
                      physical_meters, physical_feeder_frame, physical_transformer)

