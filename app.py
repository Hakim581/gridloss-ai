"""Competition demonstration UI for GridLoss AI."""

import streamlit as st

from src.dashboard.charts import balance_components, feeder_timeseries, meter_trend
from src.dashboard.components import render_kpis
from src.dashboard.network_view import render_topology
from src.detection.localization import detect
from src.evaluation.metrics import evaluate
from src.simulation.simulator import load_config, simulate


st.set_page_config(page_title="GridLoss AI", page_icon="⚡", layout="wide")
st.markdown("""<style>
.stApp {background: #101824; color: #e9f0fb}
[data-testid="stMetric"] {background: #192537; border: 1px solid #2d4058; border-radius: 10px; padding: 14px}
</style>""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Simulating network and analyzing losses…")
def run_demo(seed: int, include_incidents: bool):
    config = load_config()
    config["simulation"]["seed"] = seed
    if not include_incidents:
        config["incidents"] = []
    simulation = simulate(config)
    return simulation, detect(simulation)


st.sidebar.title("⚡ GridLoss AI")
st.sidebar.caption("Synthetic distribution network laboratory")
seed = st.sidebar.number_input("Random seed", min_value=0, max_value=999999, value=42)
include_incidents = st.sidebar.toggle("Enable demonstration incidents", value=True)
sim, result = run_demo(int(seed), include_incidents)
st.title("GridLoss AI")
st.caption("AI-Based Distribution Loss Localization & Non-Technical Loss Risk Detection")
render_kpis(sim, result)

overview, feeders_tab, meters_tab, methods_tab = st.tabs(["Network overview", "Feeder analysis", "Meter inspection", "Scenario & validation"])
with overview:
    render_topology(result.feeder_summary)
    st.subheader("Daily unexplained energy")
    st.plotly_chart(feeder_timeseries(result.feeder_daily), width="stretch")
    st.dataframe(result.feeder_summary[["feeder_id", "risk_label", "unexplained_kwh", "onset", "explanation"]], hide_index=True, width="stretch")

with feeders_tab:
    feeder = st.selectbox("Feeder", ["F1", "F2", "F3"])
    row = result.feeder_summary.set_index("feeder_id").loc[feeder]
    st.info(row.explanation)
    st.plotly_chart(balance_components(result.feeder_daily, feeder), width="stretch")
    st.dataframe(result.feeder_daily[result.feeder_daily.feeder_id == feeder][["date", "input_kwh", "metered_kwh", "estimated_missing_kwh", "expected_technical_loss_kwh", "unexplained_kwh", "risk_label"]], hide_index=True, width="stretch")

with meters_tab:
    ranked = result.meter_summary.copy()
    st.caption("Priority indicates an anomalous meter pattern and feeder context. A bypass-type load cannot be attributed to a customer from these sensors alone.")
    st.dataframe(ranked[["customer_id", "feeder_id", "risk_label", "inspection_score", "onset", "explanation"]], hide_index=True, width="stretch")
    customer = st.selectbox("Inspect meter trend", ranked.customer_id.tolist())
    st.plotly_chart(meter_trend(result.meter_daily, customer), width="stretch")
    st.caption(ranked.set_index("customer_id").loc[customer, "explanation"])

with methods_tab:
    st.subheader("Ground truth, used for demonstration only")
    st.warning("Ground truth is never passed to the detector. These synthetic events are shown so judges can compare output with known scenarios.")
    st.dataframe(sim.truth, hide_index=True, width="stretch")
    metrics = evaluate(sim, result)
    a, b, c = st.columns(3)
    a.metric("Feeder-day precision", f"{metrics['feeder_day_precision']:.0%}")
    b.metric("Feeder-day recall", f"{metrics['feeder_day_recall']:.0%}")
    c.metric("False-positive feeder-days", f"{metrics['feeder_day_false_positives']:.0f}")
    st.markdown("**Hybrid method:** measured feeder input − reported meter energy − baseline-imputed missing readings − expected I²R loss. Daily residuals are compared with a clean baseline. Isolation Forest highlights meter-level deviations; explicit rules produce inspection priorities and explanations.")
    st.caption("The network, measurements, anomalies, and truth are simulated. This prototype is not calibrated for a real utility or individual enforcement decisions.")
