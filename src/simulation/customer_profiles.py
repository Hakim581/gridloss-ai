"""Meter-level demand curves with daily, weekly and stochastic variation."""

import numpy as np
import pandas as pd


def consumption_matrix(timestamps: pd.DatetimeIndex, customers: pd.DataFrame, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    hour = timestamps.hour.to_numpy() + timestamps.minute.to_numpy() / 60
    weekend = (timestamps.dayofweek.to_numpy() >= 5).astype(float)
    result = np.empty((len(timestamps), len(customers)))
    for j, row in enumerate(customers.itertuples()):
        if row.customer_type == "Residential":
            shape = 0.36 + 0.75 * np.exp(-((hour - 7.5) / 2.5) ** 2) + 1.3 * np.exp(-((hour - 19.5) / 3.2) ** 2)
            shape *= 1 + weekend * 0.09
        else:
            business = ((hour >= 8) & (hour < 19)).astype(float)
            shape = (0.25 + 1.5 * business) * (1 - weekend * 0.48)
        modulation = 1 + 0.08 * np.sin(2 * np.pi * (timestamps.dayofyear.to_numpy() + row.profile_phase) / 9)
        noise = rng.lognormal(mean=-0.015, sigma=0.17, size=len(timestamps))
        shape = shape * modulation * noise
        result[:, j] = shape / np.mean(shape) * row.average_daily_kwh / 96
    return result
