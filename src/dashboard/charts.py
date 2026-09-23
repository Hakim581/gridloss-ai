"""Plotly figures for balances and meter trends."""

import plotly.express as px
import plotly.graph_objects as go


COLORS = {"F1": "#39c9a0", "F2": "#f29e5b", "F3": "#68a5ff"}


def feeder_timeseries(daily):
    fig = px.line(daily, x="date", y="unexplained_kwh", color="feeder_id", color_discrete_map=COLORS,
                  labels={"unexplained_kwh": "İzah olunmayan enerji (kWh/gün)", "date": "Tarix", "feeder_id": "Fider"})
    fig.add_hline(y=0, line_dash="dot", line_color="#8192aa")
    fig.update_layout(hovermode="x unified", legend_orientation="h", margin=dict(l=10, r=10, t=20, b=10))
    return fig


def balance_components(daily, feeder):
    data = daily[daily.feeder_id == feeder]
    fig = go.Figure()
    for name, col, color in [
        ("Sayğaclarda qeydə alınan", "metered_kwh", "#68a5ff"),
        ("Çatışmayan məlumatın qiymətləndirilməsi", "estimated_missing_kwh", "#bba6f7"),
        ("Gözlənilən texniki itki", "expected_technical_loss_kwh", "#39c9a0"),
        ("İzah olunmayan enerji", "unexplained_kwh", "#f29e5b"),
    ]:
        fig.add_trace(go.Bar(name=name, x=data.date, y=data[col], marker_color=color))
    fig.add_trace(go.Scatter(name="Fiderə daxil olan enerji", x=data.date, y=data.input_kwh, mode="lines", line=dict(color="#ffffff", width=2)))
    fig.update_layout(barmode="stack", hovermode="x unified", legend_orientation="h", margin=dict(l=10, r=10, t=20, b=10),
                      yaxis_title="Enerji (kWh/gün)")
    return fig


def meter_trend(daily, customer):
    data = daily[daily.customer_id == customer]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.date, y=data.reported_kwh, mode="lines+markers", name="Qeydə alınan enerji", line_color="#68a5ff"))
    fig.add_trace(go.Scatter(x=data.date, y=data.reference_kwh, mode="lines", name="Baza dövrünün gündəlik medianı", line=dict(color="#39c9a0", dash="dash")))
    fig.update_layout(hovermode="x unified", margin=dict(l=10, r=10, t=20, b=10), yaxis_title="kWh/gün", xaxis_title="Tarix")
    return fig
