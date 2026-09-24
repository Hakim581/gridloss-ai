"""Shared dashboard presentation."""

import streamlit as st


RISK_LABELS_AZ = {
    "Normal": "Normal",
    "Low Risk": "Aşağı risk",
    "Medium Risk": "Orta risk",
    "High Risk": "Yüksək risk",
    "Requires Inspection": "Yoxlama tələb olunur",
    "Data Quality Issue": "Məlumat keyfiyyəti problemi",
}


def risk_label_az(label: str) -> str:
    """Translate the detector's stable internal risk labels for the UI."""
    return RISK_LABELS_AZ.get(label, label)


def render_kpis(simulation, result):
    total = result.feeder_daily
    measured = total.input_kwh.sum()
    unexplained = total.unexplained_kwh.clip(lower=0).sum()
    watch = result.feeder_summary[result.feeder_summary.risk_label.isin(["Medium Risk", "High Risk"])]
    quality = int((simulation.meters.quality == "missing").sum())
    a, b, c, d = st.columns(4)
    a.metric("Transformatorun giriş enerjisi", f"{simulation.transformer.input_kwh.sum():,.0f} kWh")
    b.metric(
        "İzah olunmayan enerji",
        f"{unexplained:,.0f} kWh",
        help="Müsbət fider qalıqlarının cəmidir; mənfi interval qalıqları bu göstəricidən çıxılmır.",
    )
    c.metric("Riskli fiderlər", f"{len(watch)} / 3")
    d.metric("Çatışmayan sayğac intervalları", f"{quality:,}")
    st.caption(
        f"Fiderlərə daxil olan ümumi enerji: {measured:,.0f} kWh. "
        "Bütün məlumatlar sünidir; risk balı yalnız yoxlama növbəsini müəyyənləşdirir."
    )
