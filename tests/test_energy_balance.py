import numpy as np

from src.detection.energy_balance import daily_balances, interval_balances
from src.simulation.simulator import simulate


def test_balances_reconcile_and_transformer_residual_is_zero():
    sim = simulate()
    interval, transformer = interval_balances(sim)
    np.testing.assert_allclose(
        interval.input_kwh,
        interval.metered_kwh + interval.estimated_missing_kwh + interval.expected_technical_loss_kwh + interval.unexplained_kwh,
    )
    assert abs(transformer.unexplained_kwh).max() < 1e-10
    daily = daily_balances(interval)
    assert len(daily) == 90
    assert daily[daily.feeder_id == "F2"].unexplained_kwh.tail(5).mean() > 5


def test_clean_scenario_has_small_balance_residual():
    from src.simulation.simulator import load_config
    config = load_config()
    config["incidents"] = []
    sim = simulate(config)
    daily = daily_balances(interval_balances(sim)[0])
    assert daily.unexplained_kwh.abs().max() < 1e-8
