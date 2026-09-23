"""End-to-end reproducible synthetic measurements."""

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
    meters: pd.DataFrame
    feeders: pd.DataFrame
    transformer: pd.DataFrame
    truth: pd.DataFrame
    config: dict


def load_config(path: str | Path = "config/config.yaml") -> dict:
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def simulate(config: dict | None = None) -> Simulation:
    config = load_config() if config is None else config
    cfg = config["simulation"]
    hours = cfg["interval_minutes"] / 60
    periods = cfg["days"] * round(24 / hours)
    stamps = pd.date_range(cfg["start"], periods=periods, freq=f"{cfg['interval_minutes']}min")
    customers = build_network()
    true = consumption_matrix(stamps, customers, cfg["seed"])
    reported, bypass, unavailable, truth = apply_incidents(stamps, true, customers, config.get("incidents", []))

    meters = pd.DataFrame({
        "timestamp": np.repeat(stamps.to_numpy(), len(customers)),
        "customer_id": np.tile(customers.customer_id.to_numpy(), len(stamps)),
        "feeder_id": np.tile(customers.feeder_id.to_numpy(), len(stamps)),
        "reported_kwh": reported.ravel(),
        "quality": np.where(unavailable.ravel(), "missing", "ok"),
    })
    feeder_rows = []
    inputs = []
    for feeder in ("F1", "F2", "F3"):
        mask = customers.feeder_id.to_numpy() == feeder
        delivered = (true[:, mask] + bypass[:, mask]).sum(axis=1)
        physical_loss = feeder_loss_kwh(delivered, cfg["feeder_resistance_ohm"][feeder], hours, cfg["line_voltage_v"], cfg["power_factor"])
        feeder_input = delivered + physical_loss
        inputs.append(feeder_input)
        feeder_rows.append(pd.DataFrame({"timestamp": stamps, "feeder_id": feeder, "input_kwh": feeder_input}))
    feeders = pd.concat(feeder_rows, ignore_index=True)
    feeder_total = np.sum(inputs, axis=0)
    transformer = pd.DataFrame({
        "timestamp": stamps,
        "input_kwh": feeder_total + transformer_loss_kwh(feeder_total, hours, cfg["transformer_core_loss_kw"], cfg["transformer_copper_coefficient"]),
    })
    return Simulation(customers, meters, feeders, transformer, truth, config)
