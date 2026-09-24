"""Detector balances from observed channels and nominal network assumptions."""

import numpy as np
import pandas as pd

from src.simulation.technical_losses import feeder_loss_kwh, transformer_loss_kwh


def interval_balances(simulation):
    cfg = simulation.config["simulation"]
    nominal = simulation.config["detector_assumptions"]
    hours = cfg["interval_minutes"] / 60
    slots_per_hour = 60 // cfg["interval_minutes"]
    meters = simulation.meters.copy()
    meters["slot"] = meters.timestamp.dt.hour * slots_per_hour + meters.timestamp.dt.minute // cfg["interval_minutes"]
    baseline_end = meters.timestamp.min() + pd.Timedelta(days=cfg["baseline_days"])
    reference = meters.loc[meters.timestamp < baseline_end].groupby(
        ["customer_id", "slot"]
    ).reported_kwh.median().rename("reference_kwh")
    meters = meters.join(reference, on=["customer_id", "slot"])
    meters["estimated_missing_kwh"] = np.where(meters.reported_kwh.isna(), meters.reference_kwh, 0.0)
    meters["accounted_kwh"] = meters.reported_kwh.fillna(0) + meters.estimated_missing_kwh
    aggregate = meters.groupby(["timestamp", "feeder_id"], as_index=False).agg(
        metered_kwh=("reported_kwh", "sum"),
        estimated_missing_kwh=("estimated_missing_kwh", "sum"),
        missing_meters=("reported_kwh", lambda x: int(x.isna().sum())),
    )
    balance = simulation.feeders.merge(aggregate, on=["timestamp", "feeder_id"], validate="one_to_one")
    balance["accounted_kwh"] = balance.metered_kwh + balance.estimated_missing_kwh
    balance["expected_technical_loss_kwh"] = feeder_loss_kwh(
        balance.accounted_kwh.to_numpy(),
        balance.feeder_id.map(nominal["feeder_resistance_ohm"]).to_numpy(),
        hours, nominal["voltage_v"], nominal["power_factor"],
    )
    balance["unexplained_kwh"] = (
        balance.input_kwh - balance.accounted_kwh - balance.expected_technical_loss_kwh
    )
    by_time = simulation.feeders.groupby("timestamp", as_index=False).input_kwh.sum().rename(
        columns={"input_kwh": "feeder_inputs_kwh"}
    )
    transformer = simulation.transformer.merge(by_time, on="timestamp", validate="one_to_one")
    transformer["expected_technical_loss_kwh"] = transformer_loss_kwh(
        transformer.feeder_inputs_kwh.to_numpy(), hours,
        nominal["transformer_core_loss_kw"], nominal["transformer_copper_coefficient"],
    )
    transformer["unexplained_kwh"] = (
        transformer.input_kwh - transformer.feeder_inputs_kwh - transformer.expected_technical_loss_kwh
    )
    return balance, transformer


def daily_balances(interval):
    frame = interval.copy()
    frame["date"] = frame.timestamp.dt.floor("D")
    return frame.groupby(["date", "feeder_id"], as_index=False).agg(
        input_kwh=("input_kwh", "sum"), metered_kwh=("metered_kwh", "sum"),
        estimated_missing_kwh=("estimated_missing_kwh", "sum"),
        expected_technical_loss_kwh=("expected_technical_loss_kwh", "sum"),
        unexplained_kwh=("unexplained_kwh", "sum"),
        missing_meter_intervals=("missing_meters", "sum"),
    )
