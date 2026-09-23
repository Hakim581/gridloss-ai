"""Compact topology view."""

import streamlit as st

from .components import risk_label_az


def render_topology(summary):
    st.markdown("**T1 transformatoru → 3 ölçülən fider → 30 smart sayğac**")
    cols = st.columns(3)
    for col, feeder in zip(cols, ("F1", "F2", "F3")):
        row = summary.set_index("feeder_id").loc[feeder]
        with col:
            st.metric(feeder, risk_label_az(row.risk_label), f"{row.unexplained_kwh:,.0f} kWh izah olunmur")
            st.caption(f"Sayğaclar: M{(int(feeder[1])-1)*10+1:02d}–M{int(feeder[1])*10:02d}")
