# Five-minute competition demo

1. Run `streamlit run app.py`. Introduce T1, F1–F3, 30 meters, and the 30-day/15-minute simulation.
2. Show the **Network overview**. Highlight F2 unexplained energy rising on day 18. Read its explanation and kWh figure.
3. Open **Feeder analysis**, select F2, and trace feeder input against metered energy, expected technical loss, and residual. Compare F1 and F3.
4. Open **Meter inspection**. Show M17's step-down against its own baseline. Show M05 zero reporting and M27 missing telemetry as different service workflows. Explain that the F2 bypass scenario does not uniquely identify M19 from sensor data.
5. Open **Scenario & validation** to reveal injected events, precision/recall, and the clean separation of synthetic truth from scoring.
6. Turn off incidents in the sidebar. Show the normal-control behavior and explain what would need field calibration before utility deployment.
