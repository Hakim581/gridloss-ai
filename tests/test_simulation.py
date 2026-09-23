import numpy as np

from src.simulation.simulator import simulate


def test_network_and_measurements_are_reproducible():
    first = simulate()
    second = simulate()
    assert len(first.customers) == 30
    assert first.customers.groupby("feeder_id").size().to_dict() == {"F1": 10, "F2": 10, "F3": 10}
    assert len(first.meters) == 30 * 30 * 96
    assert len(first.feeders) == 3 * 30 * 96
    np.testing.assert_allclose(first.transformer.input_kwh, second.transformer.input_kwh)
    assert set(first.customers.customer_type) == {"Residential", "Small commercial"}


def test_scenario_includes_distinct_data_quality_event():
    sim = simulate()
    missing = sim.meters[sim.meters.customer_id == "M27"]
    assert missing.reported_kwh.isna().any()
    failed = sim.meters[sim.meters.customer_id == "M05"]
    assert (failed.reported_kwh == 0).any()
    assert set(sim.truth.kind) == {"under_report", "bypass_load", "meter_failure", "dropout"}
