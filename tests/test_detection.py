from src.detection.localization import detect
from src.simulation.simulator import load_config, simulate


def test_injected_feeder_is_localized_without_clean_feeder_alert():
    result = detect(simulate())
    summary = result.feeder_summary.set_index("feeder_id")
    assert summary.loc["F2", "risk_label"] == "High Risk"
    assert summary.loc["F2", "onset"].day <= 19
    assert summary.loc["F3", "risk_label"] == "Normal"
    assert summary.loc["F2", "unexplained_kwh"] > summary.loc["F1", "unexplained_kwh"]


def test_clean_control_has_no_high_risk_alert():
    config = load_config()
    config["incidents"] = []
    result = detect(simulate(config))
    assert not result.feeder_summary.risk_label.eq("High Risk").any()
