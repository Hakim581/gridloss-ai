from pathlib import Path

from streamlit.testing.v1 import AppTest


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
