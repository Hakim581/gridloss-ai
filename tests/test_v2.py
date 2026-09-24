from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from src.detection.energy_balance import interval_balances
from src.detection.localization import detect
from src.detection.risk_scoring import validate_risk_config
from src.evaluation.metrics import evaluate, evaluate_suite
from src.simulation.simulator import load_config, simulate


def scenario(kind=None, customer_id="M17", severity=0.30, seed=42):
    config = load_config()
    config["simulation"]["seed"] = seed
    config["incidents"] = [] if kind is None else [{
        "kind": kind, "customer_id": customer_id, "severity": severity,
        "start_day": 18, "duration_days": 8,
    }]
    return simulate(config)


@pytest.fixture(scope="module")
def clean():
    sim = scenario()
    return sim, detect(sim)


@pytest.fixture(scope="module")
def under_report():
    sim = scenario("under_report")
    return sim, detect(sim)


def test_network_inventory_and_reproducibility():
    a = scenario()
    b = scenario()
    assert len(a.customers) == 30
    assert a.customers.groupby("feeder_id").size().to_dict() == {"F1": 10, "F2": 10, "F3": 10}
    assert len(a.meters) == 30 * 30 * 96
    np.testing.assert_array_equal(a.meters.reported_kwh, b.meters.reported_kwh)
    np.testing.assert_array_equal(a.feeders.input_kwh, b.feeders.input_kwh)


def test_true_feeder_and_transformer_energy_conservation(clean):
    sim, _ = clean
    physical = sim.physical_feeders
    np.testing.assert_allclose(
        physical.true_input_kwh,
        physical.true_customer_kwh + physical.true_unmetered_kwh + physical.true_technical_loss_kwh,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        sim.physical_transformer.true_input_kwh,
        sim.physical_transformer.true_feeder_inputs_kwh
        + sim.physical_transformer.true_technical_loss_kwh,
        atol=1e-12,
    )


def test_measured_and_true_channels_are_distinct(clean):
    sim, result = clean
    physical = sim.physical_feeders
    observed = sim.feeders
    assert np.mean(np.abs(physical.true_input_kwh - observed.input_kwh)) > 0
    assert np.mean(np.abs(physical.true_technical_loss_kwh - result.interval.expected_technical_loss_kwh)) > 0
    assert result.transformer.unexplained_kwh.abs().mean() > 0


def test_clean_residual_varies_but_is_small_relative_to_anomaly(clean, under_report):
    _, normal = clean
    _, event = under_report
    normal_f2 = normal.feeder_daily[normal.feeder_daily.feeder_id == "F2"]
    event_f2 = event.feeder_daily[(event.feeder_daily.feeder_id == "F2")
                                  & (event.feeder_daily.date.dt.day.between(18, 25))]
    assert normal_f2.unexplained_kwh.std() > 0.02
    assert abs(normal_f2.unexplained_kwh.mean()) < 1
    assert event_f2.unexplained_kwh.mean() > normal_f2.unexplained_kwh.mean() + 2


def test_clean_network_has_no_high_risk_or_qualifying_alert(clean):
    _, result = clean
    assert not result.feeder_summary.risk_label.eq("High Risk").any()
    assert not result.feeder_daily.qualifying_alert.any()
    assert evaluate(clean[0], result)["false_positive_rate"] == 0


def test_m17_30_percent_acceptance(under_report, clean):
    _, result = under_report
    _, normal = clean
    summary = result.feeder_summary.set_index("feeder_id")
    normal_summary = normal.feeder_summary.set_index("feeder_id")
    assert summary.loc["F2", "risk_label"] == "High Risk"
    assert summary.index[0] == "F2"
    assert summary.loc["F2", "risk_score"] > normal_summary.loc["F2", "risk_score"] + 0.5
    assert summary.loc["F2", "unexplained_kwh"] > normal_summary.loc["F2", "unexplained_kwh"] + 20
    assert all(summary.loc[feeder, "risk_label"] == "Normal" for feeder in ("F1", "F3"))
    assert result.meter_summary.iloc[0].customer_id == "M17"
    assert "M17" in result.meter_summary.head(3).customer_id.tolist()
    assert "Yoxlama" in result.meter_summary.iloc[0].explanation


def test_under_reporting_semantics(under_report):
    sim, _ = under_report
    physical = sim.physical_meters
    reported = sim.meters
    selection = (physical.customer_id == "M17") & (physical.timestamp.dt.day == 18)
    ratio = reported.loc[selection, "reported_kwh"].sum() / physical.loc[selection, "true_customer_kwh"].sum()
    assert 0.68 < ratio < 0.72


def test_dropout_is_quality_not_physical_loss():
    sim = scenario("dropout", customer_id="M05", severity=1)
    result = detect(sim)
    assert sim.meters.loc[sim.meters.customer_id == "M05", "reported_kwh"].isna().any()
    assert result.meter_summary.set_index("customer_id").loc["M05", "risk_label"] == "Requires Inspection"
    assert "kifayət qədər sübut yoxdur" in result.meter_summary.set_index("customer_id").loc["M05", "explanation"]
    assert not result.feeder_daily.qualifying_alert.any()
    assert evaluate(sim, result)["fp"] == 0


def test_legitimate_high_consumption_preserves_balance():
    sim = scenario("high_consumption", severity=1.0)
    result = detect(sim)
    assert not result.feeder_daily.qualifying_alert.any()
    assert result.feeder_summary.set_index("feeder_id").loc["F2", "risk_label"] == "Normal"
    assert evaluate(sim, result)["fp"] == 0


def test_bypass_localizes_feeder_without_customer_attribution():
    sim = scenario("bypass_load", customer_id="M19", severity=0.8)
    result = detect(sim)
    assert result.feeder_summary.iloc[0].feeder_id == "F2"
    assert result.feeder_summary.iloc[0].risk_label == "High Risk"
    meter = result.meter_summary.set_index("customer_id").loc["M19"]
    assert meter.risk_label in {"Normal", "Low Risk"}
    assert "ayrı" in meter.explanation or "aid edilmir" in meter.explanation


def test_meter_failure_health_check_is_distinct_from_dropout():
    sim = scenario("meter_failure", customer_id="M05", severity=1)
    result = detect(sim)
    row = result.meter_summary.set_index("customer_id").loc["M05"]
    assert row.risk_label == "Requires Inspection"
    assert "sağlamlığı" in row.explanation
    assert sim.meters.loc[sim.meters.customer_id == "M05", "reported_kwh"].eq(0).any()
    assert sim.meters.loc[sim.meters.customer_id == "M05", "quality"].eq("missing").sum() == 0


def test_risk_bounds_and_config_thresholds(under_report):
    sim, result = under_report
    assert result.feeder_daily.risk_score.between(0, 1).all()
    assert result.meter_daily.inspection_score.between(0, 1).all()
    config = deepcopy(sim.config)
    config["risk_scoring"]["bands"]["high"] = 0.95
    changed = detect(simulate(config))
    assert changed.feeder_summary.set_index("feeder_id").loc["F2", "risk_label"] != "High Risk"
    config["risk_scoring"]["meter_weights"]["feeder_context"] = 0.3
    with pytest.raises(ValueError, match="summing to one"):
        validate_risk_config(config["risk_scoring"])


def test_event_cannot_contaminate_baseline():
    config = load_config()
    config["incidents"] = [{"kind": "under_report", "customer_id": "M17",
                            "start_day": 5, "duration_days": 2, "severity": 0.3}]
    with pytest.raises(ValueError, match="clean baseline"):
        simulate(config)


def test_detector_does_not_read_truth(under_report):
    sim, result = under_report
    sim.truth = pd.DataFrame()
    rerun = detect(sim)
    np.testing.assert_allclose(result.feeder_daily.risk_score, rerun.feeder_daily.risk_score)
    np.testing.assert_allclose(result.meter_daily.inspection_score, rerun.meter_daily.inspection_score)


def test_interval_balance_reconciles_measured_channels(under_report):
    sim, _ = under_report
    interval, transformer = interval_balances(sim)
    np.testing.assert_allclose(
        interval.input_kwh,
        interval.metered_kwh + interval.estimated_missing_kwh
        + interval.expected_technical_loss_kwh + interval.unexplained_kwh,
    )
    np.testing.assert_allclose(
        transformer.input_kwh,
        transformer.feeder_inputs_kwh + transformer.expected_technical_loss_kwh
        + transformer.unexplained_kwh,
    )


def test_multi_seed_evaluation_is_deterministic():
    names = {"Clean network", "Under-report 30%"}
    first, first_groups, first_runs = evaluate_suite(seeds=[41, 42], scenario_names=names)
    second, second_groups, second_runs = evaluate_suite(seeds=[41, 42], scenario_names=names)
    assert first == second
    pd.testing.assert_frame_equal(first_groups, second_groups)
    pd.testing.assert_frame_equal(first_runs, second_runs)
    assert first["scenarios"] == 4
    assert first["clean_controls"] == 2
    assert set(first_runs.scenario) == names
