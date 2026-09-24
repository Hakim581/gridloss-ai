"""Azerbaijani competition dashboard with reproducible scenario injection."""

import importlib

import pandas as pd
import streamlit as st

# Streamlit Cloud may hot-reload app.py without restarting its Python process.
# If V1 modules are still cached, reload dependencies in order before importing
# their V2 symbols. Ordinary fresh starts take no reload path.
from src.evaluation import metrics as _metrics_module

if not hasattr(_metrics_module, "evaluate_suite"):
    from src.simulation import anomaly_injection as _injection_module
    from src.simulation import simulator as _simulator_module
    from src.detection import energy_balance as _balance_module
    from src.detection import feature_engineering as _features_module
    from src.detection import anomaly_model as _anomaly_module
    from src.detection import risk_scoring as _risk_module
    from src.detection import localization as _localization_module

    for _module in (
        _injection_module, _simulator_module, _balance_module, _features_module,
        _anomaly_module, _risk_module, _localization_module, _metrics_module,
    ):
        importlib.reload(_module)

from src.dashboard.charts import balance_components, feeder_timeseries, meter_trend
from src.dashboard.components import render_kpis, risk_label_az
from src.dashboard.methodology import render_methodology
from src.dashboard.network_view import render_topology
from src.detection.localization import detect
from src.evaluation.metrics import evaluate_suite
from src.simulation.network import build_network
from src.simulation.simulator import load_config, simulate


EVENTS = {
    "Normal Operation": None,
    "Meter Under-Reporting": "under_report",
    "Unmetered Load": "bypass_load",
    "Meter Failure": "meter_failure",
    "Communication Dropout": "dropout",
    "Legitimate High Consumption": "high_consumption",
}
EVENTS_AZ = {
    "Normal Operation": "Normal iş rejimi",
    "Meter Under-Reporting": "Sayğacın az qeyd etməsi",
    "Unmetered Load": "Sayğacdan kənar yük",
    "Meter Failure": "Sayğac nasazlığı",
    "Communication Dropout": "Rabitə kəsilməsi",
    "Legitimate High Consumption": "Qanuni yüksək istehlak",
}


@st.cache_data(show_spinner="Şəbəkə simulyasiya edilir və itkilər təhlil olunur…")
def run_demo(seed, incident):
    config = load_config()
    config["simulation"]["seed"] = seed
    config["incidents"] = [incident] if incident else []
    simulation = simulate(config)
    return simulation, detect(simulation)


@st.cache_data(show_spinner="Çoxseedli ssenarilər hesablanır…")
def run_full_evaluation():
    return evaluate_suite()


def display_date(value):
    return "—" if pd.isna(value) else value.strftime("%d.%m.%Y")


def feeder_view(frame):
    view = frame.copy()
    view["Risk səviyyəsi"] = view.risk_label.map(risk_label_az)
    view["Başlama tarixi"] = view.onset.apply(display_date)
    view["İzah olunmayan enerji (kWh)"] = view.unexplained_kwh.round(1)
    return view[["feeder_id", "Risk səviyyəsi", "İzah olunmayan enerji (kWh)",
                 "Başlama tarixi", "explanation"]].rename(
        columns={"feeder_id": "Fider", "explanation": "Səbəb və şərh"}
    )


def meter_view(frame):
    view = frame.copy()
    view["Risk səviyyəsi"] = view.risk_label.map(risk_label_az)
    view["Yoxlama balı"] = view.inspection_score.round(2)
    view["Başlama tarixi"] = view.onset.apply(display_date)
    return view[["customer_id", "feeder_id", "Risk səviyyəsi", "Yoxlama balı",
                 "Başlama tarixi", "explanation"]].rename(
        columns={"customer_id": "Sayğac", "feeder_id": "Fider",
                 "explanation": "Səbəb və tövsiyə"}
    )


st.set_page_config(page_title="GridLoss AI", page_icon="⚡", layout="wide")
st.markdown("""<style>
.stApp {background: #101824; color: #e9f0fb}
[data-testid="stMetric"] {background: #192537; border: 1px solid #2d4058; border-radius: 10px; padding: 14px}
</style>""", unsafe_allow_html=True)

if "active_incident" not in st.session_state:
    st.session_state.active_incident = None
if "evaluation_result" not in st.session_state:
    st.session_state.evaluation_result = None

st.sidebar.title("⚡ GridLoss AI")
st.sidebar.caption("Sintetik elektrik paylayıcı şəbəkə laboratoriyası")
seed = int(st.sidebar.number_input(
    "Simulyasiya variantı (seed)", min_value=0, max_value=999999, value=42,
    help="Eyni rəqəm eyni sintetik şəbəkəni yaradır."
))
st.title("GridLoss AI")
st.caption("Paylayıcı şəbəkədə enerji itkisinin lokallaşdırılması və qeyri-texniki itki riskinin aşkarlanması")

overview, model_tab, feeders_tab, meters_tab, scenario_tab, performance_tab, method_tab = st.tabs([
    "Şəbəkəyə baxış", "Model necə işləyir?", "Fider təhlili", "Sayğac yoxlaması",
    "Ssenari simulyatoru", "Model performansı", "Metodologiya"
])

# Place controls before the simulation call so button clicks recompute every view in the same run.
with scenario_tab:
    st.header("Ssenari simulyatoru")
    st.write("Hadisəni seçib şəbəkəni yenidən hesablayın. Eyni seed və ssenari eyni nəticəni verir.")
    inventory = build_network()
    feeder = st.selectbox("Select Feeder / Fider", ["F1", "F2", "F3"], index=1)
    choices = inventory.loc[inventory.feeder_id == feeder, "customer_id"].tolist()
    customer = st.selectbox(
        "Select Customer / Meter / Sayğac", choices,
        index=choices.index("M17") if "M17" in choices else 0
    )
    event_label = st.selectbox(
        "Select Event Type / Hadisə", list(EVENTS),
        index=1, format_func=lambda value: EVENTS_AZ[value]
    )
    severity_pct = st.slider("Select Severity / Təsir (%)", 0, 150, 30, 5)
    start_day = st.slider("Select Start Day / Başlanğıc gün", 11, 30, 18)
    start_hour = st.selectbox("Select Start Time / Saat", list(range(24)), index=0)
    duration = st.slider("Select Duration / Müddət (gün)", 1, 20, 8)
    inject, reset = st.columns(2)
    if inject.button("INJECT SCENARIO / SSENARİNİ TƏTBİQ ET", type="primary"):
        kind = EVENTS[event_label]
        if kind == "under_report" and severity_pct > 100:
            st.error("Az qeyd etmə 100%-dən çox ola bilməz.")
        else:
            st.session_state.active_incident = (
                {"kind": kind, "customer_id": customer, "start_day": start_day,
                 "start_hour": start_hour, "duration_days": duration,
                 "severity": severity_pct / 100}
                if kind else None
            )
    if reset.button("RESET SIMULATION / SİMULYASİYANI SIFIRLA"):
        st.session_state.active_incident = None
    active = st.session_state.active_incident
    if active:
        st.info(
            f"Aktiv: {active['kind']} · {active['customer_id']} · "
            f"{active['severity']:.0%} · gün {active['start_day']} · {active['duration_days']} gün"
        )
    else:
        st.success("Normal şəbəkə aktivdir.")
    st.caption("Risk balı yoxlama prioritetidir; oğurluq ehtimalı və ya günah sübutu deyil.")

sim, result = run_demo(seed, st.session_state.active_incident)
render_kpis(sim, result)

with overview:
    render_topology(result.feeder_summary)
    st.subheader("Gündəlik izah olunmayan enerji")
    st.plotly_chart(feeder_timeseries(result.feeder_daily), width="stretch")
    st.dataframe(feeder_view(result.feeder_summary), hide_index=True, width="stretch")

with model_tab:
    render_methodology(sim, result)

with feeders_tab:
    selected_feeder = st.selectbox("Fideri seçin", ["F1", "F2", "F3"])
    row = result.feeder_summary.set_index("feeder_id").loc[selected_feeder]
    st.metric("Risk səviyyəsi", risk_label_az(row.risk_label), f"Risk balı: {row.risk_score:.2f}")
    st.info(row.explanation)
    st.plotly_chart(balance_components(result.feeder_daily, selected_feeder), width="stretch")
    view = result.feeder_daily[result.feeder_daily.feeder_id == selected_feeder].copy()
    view["Risk səviyyəsi"] = view.risk_label.map(risk_label_az)
    st.dataframe(view[["date", "input_kwh", "metered_kwh", "estimated_missing_kwh",
                       "expected_technical_loss_kwh", "unexplained_kwh",
                       "data_quality_issue", "Risk səviyyəsi"]], hide_index=True, width="stretch")

with meters_tab:
    ranked = result.meter_summary.copy()
    st.caption("Yoxlama prioriteti sayğac davranışı ilə fider kontekstini birləşdirir. "
               "Sayğacdan kənar yük konkret müştəriyə aid edilmir.")
    st.dataframe(meter_view(ranked), hide_index=True, width="stretch")
    selected_customer = st.selectbox("Trendinə baxılacaq sayğac", ranked.customer_id.tolist())
    st.plotly_chart(meter_trend(result.meter_daily, selected_customer), width="stretch")
    selected = ranked.set_index("customer_id").loc[selected_customer]
    st.info(f"{risk_label_az(selected.risk_label)}: {selected.explanation}")

with performance_tab:
    st.header("Model performansı")
    st.warning("Synthetic validation is not equivalent to real utility field accuracy.")
    st.write("Tam yoxlama müxtəlif seed-lər və hadisə gücləri üzrə yalnız düymə basıldıqda işləyir.")
    if st.button("Çoxseedli qiymətləndirməni hesabla"):
        st.session_state.evaluation_result = run_full_evaluation()
    if st.session_state.evaluation_result is not None:
        metrics, by_scenario, runs = st.session_state.evaluation_result
        cols = st.columns(3)
        cols[0].metric("Precision", f"{metrics['precision']:.1%}")
        cols[1].metric("Recall", f"{metrics['recall']:.1%}")
        cols[2].metric("F1", f"{metrics['f1']:.1%}")
        cols = st.columns(3)
        cols[0].metric("False Positive Rate", f"{metrics['false_positive_rate']:.1%}")
        cols[1].metric("Fider lokallaşdırma dəqiqliyi", f"{metrics['feeder_localization_accuracy']:.1%}")
        cols[2].metric("Orta aşkarlama gecikməsi", f"{metrics['average_detection_delay_hours']:.1f} saat")
        st.caption(
            f"{metrics['scenarios']} icra edilmiş ssenari · {metrics['seeds']} seed · "
            f"{metrics['clean_controls']} təmiz nəzarət · "
            f"{metrics['undetected_events']} aşkarlanmamış fiziki hadisə. "
            "FPR = yanlış müsbət fider-gün / bütün həqiqi mənfi fider-gün. "
            "Gecikmə yalnız aşkarlanan hadisələr üzrədir; aşkarlanmayanlar ayrıca sayılır."
        )
        st.dataframe(by_scenario, hide_index=True, width="stretch")
        st.bar_chart(by_scenario.set_index("scenario")["detection_rate"])
        with st.expander("Seed üzrə nəticələr"):
            st.dataframe(runs, hide_index=True, width="stretch")

with method_tab:
    st.header("Metodologiya və məhdudiyyətlər")
    st.write("Fiziki simulyasiya həqiqi xətt parametrlərindən, detektor isə nominal "
             "parametrlərdən istifadə edir. Sayğac və fider sensorlarına kiçik ölçmə xətası əlavə olunur. "
             "İlk 10 təmiz gün normal qalıq variasiyasını öyrədir; hadisə bu dövrdə başlaya bilməz.")
    st.write("Transformator balansı müstəqil səs-küylü ölçmələr üçün sistem səviyyəsində "
             "uyğunluq yoxlamasıdır. Isolation Forest balı davranış anomaliyasıdır, ehtimal deyil.")
    st.warning("GridLoss AI qərar dəstəyidir. Yüksək risk yalnız mühəndis yoxlaması üçün prioritetdir; "
               "avtomatik cəza və ya oğurluq sübutu deyil.")
    if len(sim.truth):
        with st.expander("Sintetik ssenari həqiqəti (yalnız qiymətləndirmə üçün)"):
            st.dataframe(sim.truth, hide_index=True, width="stretch")
    st.caption("Gələcək kommunal inteqrasiya: AMI, fider və transformator sayğacları, SCADA, GIS, OMS, "
               "aktiv reyestri və sahə yoxlamaları. Hazırda heç bir real kommunal sistemə qoşulmur.")
