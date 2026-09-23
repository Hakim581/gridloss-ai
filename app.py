"""GridLoss AI müsabiqə nümayişi üçün Streamlit interfeysi."""

import pandas as pd
import streamlit as st

from src.dashboard.charts import balance_components, feeder_timeseries, meter_trend
from src.dashboard.components import render_kpis, risk_label_az
from src.dashboard.methodology import render_methodology
from src.dashboard.network_view import render_topology
from src.detection.localization import detect
from src.evaluation.metrics import evaluate
from src.simulation.simulator import load_config, simulate


st.set_page_config(page_title="GridLoss AI", page_icon="⚡", layout="wide")
st.markdown(
    """<style>
.stApp {background: #101824; color: #e9f0fb}
[data-testid="stMetric"] {background: #192537; border: 1px solid #2d4058; border-radius: 10px; padding: 14px}
</style>""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Şəbəkə simulyasiya edilir və itkilər təhlil olunur…")
def run_demo(seed: int, include_incidents: bool):
    config = load_config()
    config["simulation"]["seed"] = seed
    if not include_incidents:
        config["incidents"] = []
    simulation = simulate(config)
    return simulation, detect(simulation)


def display_date(value) -> str:
    return "—" if pd.isna(value) else value.strftime("%d.%m.%Y")


def localized_feeder_summary(frame):
    view = frame.copy()
    view["Risk səviyyəsi"] = view.risk_label.map(risk_label_az)
    view["Başlama tarixi"] = view.onset.apply(display_date)
    view["İzah olunmayan enerji (kWh)"] = view.unexplained_kwh.round(1)
    return view[["feeder_id", "Risk səviyyəsi", "İzah olunmayan enerji (kWh)", "Başlama tarixi", "explanation"]].rename(
        columns={"feeder_id": "Fider", "explanation": "Səbəb və şərh"}
    )


def localized_meter_summary(frame):
    view = frame.copy()
    view["Risk səviyyəsi"] = view.risk_label.map(risk_label_az)
    view["Yoxlama balı"] = view.inspection_score.round(2)
    view["Başlama tarixi"] = view.onset.apply(display_date)
    return view[["customer_id", "feeder_id", "Risk səviyyəsi", "Yoxlama balı", "Başlama tarixi", "explanation"]].rename(
        columns={"customer_id": "Sayğac", "feeder_id": "Fider", "explanation": "Səbəb və tövsiyə"}
    )


st.sidebar.title("⚡ GridLoss AI")
st.sidebar.caption("Süni elektrik paylayıcı şəbəkə laboratoriyası")
seed = st.sidebar.number_input(
    "Simulyasiya variantı (seed)",
    min_value=0,
    max_value=999999,
    value=42,
    help="Eyni rəqəm eyni sintetik istehlak profilini yaradır.",
)
include_incidents = st.sidebar.toggle(
    "Demo anomaliyalarını aktiv et",
    value=True,
    help="Söndürüldükdə sistem normal nəzarət ssenarisi ilə işləyir.",
)
sim, result = run_demo(int(seed), include_incidents)

st.title("GridLoss AI")
st.caption("Paylayıcı şəbəkədə enerji itkisinin lokallaşdırılması və qeyri-texniki itki riskinin aşkarlanması")
st.info(
    "Sistem fiderə daxil olan enerji ilə sayğaclarda qeydə alınan enerji və gözlənilən texniki itkini "
    "müqayisə edir. Qalan fərq izah olunmayan enerji kimi göstərilir; ML isə yoxlanmalı sayğacları prioritetləşdirir."
)
render_kpis(sim, result)

overview, model_tab, feeders_tab, meters_tab, methods_tab = st.tabs(
    ["Şəbəkəyə baxış", "Model necə işləyir?", "Fider təhlili", "Sayğac yoxlaması", "Ssenari və qiymətləndirmə"]
)

with overview:
    render_topology(result.feeder_summary)
    st.subheader("Gündəlik izah olunmayan enerji")
    st.caption("Qrafikdə sıfırdan yuxarı davamlı artım fider balansında əlavə araşdırma tələb edən fərqi göstərir.")
    st.plotly_chart(feeder_timeseries(result.feeder_daily), width="stretch")
    st.dataframe(localized_feeder_summary(result.feeder_summary), hide_index=True, width="stretch")

with model_tab:
    render_methodology(sim, result)

with feeders_tab:
    feeder = st.selectbox("Fideri seçin", ["F1", "F2", "F3"])
    row = result.feeder_summary.set_index("feeder_id").loc[feeder]
    st.metric("Risk səviyyəsi", risk_label_az(row.risk_label), f"Risk balı: {row.risk_score:.2f}")
    st.info(row.explanation)
    st.plotly_chart(balance_components(result.feeder_daily, feeder), width="stretch")
    feeder_view = result.feeder_daily[result.feeder_daily.feeder_id == feeder].copy()
    feeder_view["Risk səviyyəsi"] = feeder_view.risk_label.map(risk_label_az)
    feeder_view = feeder_view.rename(
        columns={
            "date": "Tarix",
            "input_kwh": "Fider girişi (kWh)",
            "metered_kwh": "Sayğac enerjisi (kWh)",
            "estimated_missing_kwh": "Çatışmayan məlumat üçün qiymət (kWh)",
            "expected_technical_loss_kwh": "Gözlənilən texniki itki (kWh)",
            "unexplained_kwh": "İzah olunmayan enerji (kWh)",
        }
    )
    st.dataframe(
        feeder_view[["Tarix", "Fider girişi (kWh)", "Sayğac enerjisi (kWh)", "Çatışmayan məlumat üçün qiymət (kWh)", "Gözlənilən texniki itki (kWh)", "İzah olunmayan enerji (kWh)", "Risk səviyyəsi"]],
        hide_index=True,
        width="stretch",
    )

with meters_tab:
    ranked = result.meter_summary.copy()
    st.caption(
        "Prioritet sayğacın öz istehlak nümunəsini və aid olduğu fiderin vəziyyətini birləşdirir. "
        "Sayğacdan kənar əlavə yükü bu sensorlarla konkret müştəriyə aid etmək mümkün deyil."
    )
    st.dataframe(localized_meter_summary(ranked), hide_index=True, width="stretch")
    customer = st.selectbox("Trendinə baxılacaq sayğac", ranked.customer_id.tolist())
    st.plotly_chart(meter_trend(result.meter_daily, customer), width="stretch")
    selected = ranked.set_index("customer_id").loc[customer]
    st.info(f"{risk_label_az(selected.risk_label)}: {selected.explanation}")

with methods_tab:
    st.subheader("Demo üçün məlum ssenarilər")
    st.warning(
        "Aşağıdakı ssenari məlumatları aşkarlama modelinə verilmir. Onlar yalnız sintetik nəticəni məlum hadisələrlə müqayisə etmək üçündür."
    )
    truth = sim.truth.copy()
    truth["Hadisə"] = truth.kind.map(
        {
            "under_report": "Sayğacın az qeyd etməsi",
            "bypass_load": "Sayğacdan kənar əlavə yük",
            "meter_failure": "Sayğac nasazlığı",
            "dropout": "Rabitə kəsilməsi",
        }
    )
    truth["Başlanğıc"] = truth.start.dt.strftime("%d.%m.%Y %H:%M")
    truth["Son"] = truth.end.dt.strftime("%d.%m.%Y %H:%M")
    truth["Təsir əmsalı"] = truth.severity
    st.dataframe(
        truth[["customer_id", "feeder_id", "Hadisə", "Başlanğıc", "Son", "Təsir əmsalı"]].rename(
            columns={"customer_id": "Sayğac", "feeder_id": "Fider"}
        ),
        hide_index=True,
        width="stretch",
    )
    metrics = evaluate(sim, result)
    a, b, c = st.columns(3)
    a.metric("Fider-gün dəqiqliyi", f"{metrics['feeder_day_precision']:.0%}")
    b.metric("Fider-gün aşkarlama əhatəsi", f"{metrics['feeder_day_recall']:.0%}")
    c.metric("Yanlış xəbərdarlıq verilən fider-gün", f"{metrics['feeder_day_false_positives']:.0f}")
    st.caption(
        "Bu göstəricilər yalnız əvvəlcədən məlum olan sintetik hadisələr üzrə hesablanır. Real şəbəkədə tətbiqdən əvvəl "
        "xətt müqaviməti, mövsümi profil, sayğac səhvi və sahə yoxlamaları ilə kalibrasiya tələb olunur."
    )
