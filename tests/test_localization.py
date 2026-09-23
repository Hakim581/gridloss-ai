from src.detection.localization import detect
from src.simulation.simulator import simulate


def test_meter_pattern_and_data_quality_are_separated():
    summary = detect(simulate()).meter_summary.set_index("customer_id")
    assert summary.loc["M17", "inspection_score"] > summary.loc["M19", "inspection_score"]
    assert summary.loc["M05", "risk_label"] == "Requires Inspection"
    assert summary.loc["M27", "risk_label"] == "Requires Inspection"
    assert "ayrıca anomaliya görünmür" in summary.loc["M19", "explanation"] or summary.loc["M19", "risk_label"] in {"Normal", "Low Risk"}
