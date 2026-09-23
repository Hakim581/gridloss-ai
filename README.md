# GridLoss AI

**AI-Based Distribution Loss Localization & Non-Technical Loss Risk Detection System**

A runnable, synthetic low-voltage utility demonstration: one transformer (T1), three feeders (F1–F3), 30 smart meters (M01–M30), 30 days of 15-minute measurements, and four controlled incidents. The dashboard combines feeder energy balances, an electrical loss estimate, statistical baseline comparison, and Isolation Forest meter anomaly scores. It reports unexplained energy and inspection priorities with plain-language explanations.

## Quick start

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit. The demo generates all data in memory on first load; no credentials or external services are needed. Use the sidebar toggle to compare the injected scenario with a clean control. Changing the seed makes a reproducible new run.

To export CSVs and run tests:

```bash
python -m src.utils.export_data
python -m pytest -q
```

## What the demo shows

- **F2:** M17 under-reports starting day 18; an additional unmetered load is assigned to the F2 scenario starting day 21. Feeder input sensors localize unexplained energy to F2. The unmetered load cannot be attributed to M19 from the observed readings alone.
- **F1:** M05 reports zeros for four days, supporting a meter inspection recommendation.
- **F3:** M27 has a communication dropout. Baseline-imputed energy prevents missing telemetry from being treated as confirmed physical loss; the meter is flagged for data-quality inspection.
- **Normal variation:** realistic household and small-commercial daily profiles, weekends, and noise are present throughout.

All dates, measurements, and customer IDs are synthetic. A risk label is a workflow aid, not an allegation about a person. No real utility data or individual enforcement decision is supported by this prototype.

## Project map

`config/config.yaml` controls topology-independent simulation settings and incidents. `src/simulation/` creates the network and sensor readings. `src/detection/` computes the physics balance, ML features, and explainable risk. `src/evaluation/` evaluates feeder-day alerts against synthetic truth kept separate from scoring. `src/dashboard/` contains visuals. `docs/` explains method, architecture, and a live demo script.
