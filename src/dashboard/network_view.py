"""Compact topology view."""

import streamlit as st


def render_topology(summary):
    st.markdown("**T1 transformer → three instrumented feeders → 30 meters**")
    cols = st.columns(3)
    for col, feeder in zip(cols, ("F1", "F2", "F3")):
        row = summary.set_index("feeder_id").loc[feeder]
        with col:
            st.metric(feeder, row.risk_label, f"{row.unexplained_kwh:,.0f} kWh unexplained")
            st.caption(f"Meters M{(int(feeder[1])-1)*10+1:02d}–M{int(feeder[1])*10:02d}")
