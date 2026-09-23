"""Plain-language, data-backed explanation of the hybrid detector."""

import pandas as pd
import streamlit as st

from .components import risk_label_az


def render_methodology(simulation, result):
    """Explain inputs, calculations, scores, and interpretation in Azerbaijani."""
    st.header("Model necə işləyir?")
    st.write(
        "GridLoss AI bir müştərini avtomatik günahlandırmır. Sistem əvvəlcə elektrik enerjisinin "
        "fiziki balansını hesablayır, sonra normal davranışdan yayınmanı ML ilə tapır və nəticəni "
        "yoxlama prioritetinə çevirir."
    )

    step1, step2, step3, step4 = st.columns(4)
    step1.info("**1. Ölçmə**\n\nTransformator, fider və 30 sayğacdan 15 dəqiqəlik enerji göstəriciləri alınır.")
    step2.info("**2. Fiziki balans**\n\nFiderə daxil olan enerji sayğaclar və hesablanmış texniki itki ilə müqayisə edilir.")
    step3.info("**3. Anomaliya modeli**\n\nİlk 10 gün baza kimi götürülür. Isolation Forest qeyri-adi sayğac davranışını tapır.")
    step4.info("**4. Risk və izah**\n\nFider qalığı, ML balı və istehlak azalması yoxlama növbəsinə və mətn izahına çevrilir.")

    st.subheader("1. Enerji balansı — əsas mühəndislik hesabı")
    st.latex(
        r"E_{izah\ olunmayan}=E_{fider\ girişi}-E_{sayğaclar}-E_{çatışmayan\ məlumat}-E_{texniki\ itki}"
    )
    st.write(
        "Texniki itki sadələşdirilmiş üçfazalı xətt modeli ilə hesablanır: "
        "cərəyan yükdən tapılır, sonra xətt itkisi $3I^2R\\Delta t$ kimi qiymətləndirilir. "
        "Rabitəsi kəsilmiş sayğac üçün eyni saatın baza medianı müvəqqəti qiymət kimi istifadə olunur "
        "və məlumat keyfiyyəti ayrıca işarələnir."
    )

    feeder_id = result.feeder_summary.iloc[0].feeder_id
    feeder_days = result.feeder_daily[result.feeder_daily.feeder_id == feeder_id]
    peak = feeder_days.loc[feeder_days.unexplained_kwh.idxmax()]
    accounted = peak.metered_kwh + peak.estimated_missing_kwh
    st.markdown(f"**Real nümunə — {feeder_id}, {peak.date.date()}**")
    st.code(
        f"{peak.input_kwh:.1f} kWh fider girişi\n"
        f"− {peak.metered_kwh:.1f} kWh sayğaclarda qeydə alınan\n"
        f"− {peak.estimated_missing_kwh:.1f} kWh çatışmayan məlumat üçün qiymət\n"
        f"− {peak.expected_technical_loss_kwh:.1f} kWh gözlənilən texniki itki\n"
        f"= {peak.unexplained_kwh:.1f} kWh izah olunmayan enerji"
    )
    st.caption(
        f"Bu gündə sayğaclarla uçota alınmış ümumi enerji {accounted:.1f} kWh-dır. "
        "Nəticə ölçülmüş fider girişi ilə fiziki balans arasındakı qalıqdır."
    )

    st.subheader("2. ML modeli nəyi yoxlayır?")
    st.write(
        "Isolation Forest hər sayğac üçün üç gündəlik əlamətə baxır: istehlakın öz baza səviyyəsinə "
        "nisbəti, sıfır göstəricilərin payı və çatışmayan göstəricilərin payı. Həftəsonu ilə iş günü "
        "ayrıca müqayisə olunur. Model yalnız ilk 10 günlük təmiz baza dövrü ilə öyrədilir."
    )
    st.warning(
        "ML balı oğurluq ehtimalı deyil. O, normal nümunədən yayınmanın ölçüsüdür və mühəndis "
        "yoxlamasını prioritetləşdirmək üçün istifadə olunur."
    )

    st.subheader("3. Risk balı necə yaranır?")
    left, right = st.columns(2)
    with left:
        st.markdown("**Fider risk balı**")
        st.write(
            "55% — izah olunmayan enerjinin baza dövründən statistik yayınması  \n"
            "45% — izah olunmayan enerjinin gözlənilən texniki itkiyə nisbəti"
        )
    with right:
        st.markdown("**Sayğac yoxlama balı**")
        st.write(
            "62% — istehlakın öz baza səviyyəsindən azalması  \n"
            "18% — Isolation Forest anomaliya balı  \n"
            "20% — həmin fiderin risk balı"
        )

    st.markdown(
        "**Hədlər:** 0–0.24 Normal · 0.25–0.51 Aşağı risk · 0.52–0.77 Orta risk · "
        "0.78–1.00 Yüksək risk. Məlumatın yarıdan çoxu çatışmırsa və ya sayğac əsasən sıfır "
        "göstərirsə, nəticə birbaşa “Yoxlama tələb olunur” kimi verilir."
    )

    st.subheader("4. Cari nəticəni necə oxumaq lazımdır?")
    summary = result.feeder_summary.copy()
    summary["Risk səviyyəsi"] = summary.risk_label.map(risk_label_az)
    summary["Başlama tarixi"] = summary.onset.apply(_date_or_dash)
    summary["Risk balı"] = summary.risk_score.round(2)
    summary["İzah olunmayan enerji (kWh)"] = summary.unexplained_kwh.round(1)
    st.dataframe(
        summary[["feeder_id", "Risk səviyyəsi", "Risk balı", "İzah olunmayan enerji (kWh)", "Başlama tarixi", "explanation"]]
        .rename(columns={"feeder_id": "Fider", "explanation": "Mühəndis izahı"}),
        hide_index=True,
        width="stretch",
    )
    st.success(
        "Qərar qaydası: əvvəl fider səviyyəsində enerji uyğunsuzluğu təsdiqlənir, sonra sayğac davranışı "
        "yoxlama növbəsini daraldır. Fiderdəki sayğacdan kənar yükü təkcə bu məlumatlarla konkret "
        "müştəriyə aid etmək mümkün deyil."
    )


def _date_or_dash(value) -> str:
    return "—" if pd.isna(value) else value.strftime("%d.%m.%Y")
