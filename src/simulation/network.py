"""Deterministic low-voltage network inventory."""

import pandas as pd


def build_network() -> pd.DataFrame:
    """Return one transformer, three feeders, and 30 customer meters."""
    rows = []
    for index in range(1, 31):
        feeder = f"F{(index - 1) // 10 + 1}"
        kind = "Small commercial" if index in {4, 9, 14, 19, 24, 29} else "Residential"
        daily = (20 + (index % 5) * 3) if kind == "Small commercial" else (7 + (index % 6) * 1.2)
        rows.append({
            "transformer_id": "T1", "feeder_id": feeder,
            "customer_id": f"M{index:02d}", "customer_type": kind,
            "contracted_power_kw": 8.0 if kind == "Small commercial" else 4.0,
            "average_daily_kwh": float(daily),
            "profile_phase": float((index * 7) % 24) / 24,
        })
    return pd.DataFrame(rows)
