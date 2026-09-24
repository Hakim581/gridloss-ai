from pathlib import Path

from streamlit.testing.v1 import AppTest
from src.evaluation import metrics


def test_streamlit_scenario_injection_and_reset():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=60).run()
    assert not app.exception
    assert len(app.tabs) == 7
    assert app.session_state["active_incident"] is None
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["active_incident"]["customer_id"] == "M17"
    assert app.session_state["active_incident"]["severity"] == 0.30
    app.button[1].click().run()
    assert not app.exception
    assert app.session_state["active_incident"] is None


def test_streamlit_recovers_stale_cached_modules():
    del metrics.evaluate_suite
    try:
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=60).run()
        assert not app.exception
        assert len(app.tabs) == 7
        assert hasattr(metrics, "evaluate_suite")
    finally:
        import importlib

        importlib.reload(metrics)
