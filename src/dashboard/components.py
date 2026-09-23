"""Shared dashboard presentation."""

import streamlit as st


def render_kpis(simulation, result):
    total = result.feeder_daily
    measured = total.input_kwh.sum()
    unexplained = total.unexplained_kwh.clip(lower=0).sum()
    watch = result.feeder_summary[result.feeder_summary.risk_score >= 0.52]
    quality = int((simulation.meters.quality == "missing").sum())
    a, b, c, d = st.columns(4)
    a.metric("Transformer input", f"{simulation.transformer.input_kwh.sum():,.0f} kWh")
    b.metric("Unexplained energy", f"{unexplained:,.0f} kWh", help="Sum of positive feeder residuals; interval negative residuals are not netted here.")
    c.metric("Feeder alerts", f"{len(watch)} / 3")
    d.metric("Missing meter intervals", f"{quality:,}")
    st.caption(f"Feeder input total: {measured:,.0f} kWh. Synthetic observations; risk scores support inspection prioritization only.")
