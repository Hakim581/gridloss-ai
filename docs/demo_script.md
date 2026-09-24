# Four-to-five-minute competition demonstration

1. **0:00–0:35 — Normal network.** Open the app and show T1, F1–F3 and the 30 meters. Explain that small residual variation comes from sensor error and uncertain line parameters. All three feeders should be free of sustained High Risk alerts.
2. **0:35–1:05 — Physics.** In **Model necə işləyir?**, show measured feeder input minus reported meter energy, missing-read estimate and nominal I²R technical loss. Point out that the simulator's true line parameters differ from the detector's nominal settings.
3. **1:05–2:15 — Primary case.** Open **Ssenari simulyatoru**. Select F2, M17, Meter Under-Reporting, 30%, start day 18, eight days. Click **INJECT SCENARIO**. Explain that 10 kWh true energy appears as about 7 kWh reported. Show F2 residual growth, High Risk localization, and F1/F3 remaining normal.
4. **2:15–2:50 — Inspection priority.** Open **Sayğac yoxlaması**. M17 should lead the candidate ranking, with a visible consumption drop and F2 balance context. Say explicitly: a risk index recommends inspection; it does not prove theft.
5. **2:50–3:30 — Telemetry control.** Reset. Select M05 and Communication Dropout; inject. Show missing data and the telemetry warning. No physical NTL attribution should appear.
6. **3:30–3:55 — Legitimate load.** Reset and inject Legitimate High Consumption at M17. Both physical and reported energy rise. Show that increased demand alone does not trigger a sustained feeder-loss alert.
7. **3:55–4:35 — Validation.** Open **Model performansı**. Run the cached, on-demand multi-seed suite before the presentation if time is constrained. Read executed precision, recall, F1, FPR, localization, delay, seed count, and the 10/20/30/40% rows. Acknowledge that 10% may be weak and undetected events are counted.
8. **4:35–5:00 — Boundaries.** Explain that bypass load can identify a feeder without naming a customer. End with the future AMI/SCADA/GIS integration concept and the need for field calibration.
