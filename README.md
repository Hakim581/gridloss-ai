# GridLoss AI V2

GridLoss AI is a **synthetic decision support prototype** for distribution feeder loss localization and meter inspection priority. It models one transformer, three feeders, 30 customers, and 30 days of 15-minute readings. Its Azerbaijani Streamlit dashboard lets a judge inject a single event, reset to normal operation, and run a separate multi-seed evaluation.

The default selectable demo is **M17 on F2, 30% meter under-reporting**: about 10 kWh physically delivered corresponds to about 7 kWh reported. The app opens in normal operation so the difference is visible after injection. A high risk score is a normalized inspection priority index, **not a theft probability or proof of misconduct**.

## Run locally

Python 3.10+ is required.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q -W default
python -m streamlit run app.py
```

To run the full configured 10-seed validation on demand:

```bash
python -m src.evaluation.run
```

The command writes computed JSON and CSV results under `data/generated/`. The dashboard's **Model performansı** tab runs the same evaluation only when its button is clicked and caches the result. Ordinary page reruns run one interactive scenario.

## Demonstration

1. Start with the normal network. F1, F2, and F3 should have no sustained High Risk alert; small residual variation remains.
2. In **Ssenari simulyatoru**, choose F2, M17, Meter Under-Reporting, 30%, day 18, eight days; click **INJECT SCENARIO**. F2 becomes the highest risk feeder and M17 is the leading inspection candidate.
3. Reset, inject a Communication Dropout at M05. The missing reads produce a data quality / telemetry check, without automatic physical-loss attribution.
4. Reset, inject Legitimate High Consumption. Physical and reported energy rise together, so high demand alone should not imply non-technical loss.
5. For Unmetered Load, the feeder can be localized; an otherwise normal meter cannot be named as the cause.

All measurements, events, and customer identifiers are synthetic. There is no current Azerishiq integration or real customer data.

## Engineering boundary

The simulator uses hidden true feeder resistance, temperature adjustment, voltage, power factor, and physical load. Independent meter and feeder sensor readings include modest configurable error and rounding. The detector receives only the reported meter readings, measured feeder inputs, measured transformer input, inventory, and nominal electrical parameters. True state and event labels are held outside detection.

The detector estimates `3 I²R Δt` loss from nominal parameters and computes measured feeder input minus accounted meter energy and expected loss. A clean ten-day pre-event period calibrates normal residual variation. Two consecutive medium-risk days are required for a feeder alert. Missing telemetry is flagged and blocks physical-loss classification for affected feeder-days. The transformer balance is a noisy system-level sanity check.

Isolation Forest uses three explainable daily meter features: consumption relative to a weekday/weekend baseline, zero-read fraction, and missing-read fraction. It is trained only on the clean calibration window. Its score is a behavioral anomaly index, not a calibrated probability. Configured weights combine that signal with consumption drop and confirmed feeder context for inspection ranking. See [methodology](docs/methodology.md) and [architecture](docs/architecture.md).

## Validation

The evaluation harness executes clean controls; 10%, 20%, 30%, and 40% under-reporting; unmetered load; meter failure; communication dropout; and legitimate high consumption for each configured seed. Metrics are computed from post-baseline feeder-days and kept separate from detector inputs. Precision, recall, F1, false-positive rate, feeder localization accuracy, and delay are defined in [methodology](docs/methodology.md). Undetected events are counted explicitly and excluded from the detected-event delay average.

Synthetic validation does **not** measure field accuracy. A real pilot needs calibrated line and meter data, topology validation, seasonal baselines, known inspection outcomes, and human review. See [competition notes](docs/competition_notes.md).

The configured 10-seed run was executed for V2 (90 scenarios; 10 clean controls). It produced feeder-day precision **100%** (293/293), recall **61.0%** (293/480), F1 **75.8%**, and false-positive rate **0%** (0/4,920 true-negative feeder-days). Event-level feeder localization was **83.3%** (50/60 physical events). The mean delay among 50 detected physical events was **75.36 hours**; 10 physical events were undetected. These values describe this synthetic setup and its chosen seeds only.

| Under-reporting severity | Detected runs | Mean detected-event delay |
| --- | ---: | ---: |
| 10% | 0/10 | Not defined (undetected) |
| 20% | 10/10 | 184.8 h |
| 30% | 10/10 | 48.0 h |
| 40% | 10/10 | 48.0 h |

## Repository map

- `config/config.yaml`: truth, detector, measurement, scoring, and evaluation settings.
- `src/simulation/`: physical state, events, and measured channels.
- `src/detection/`: balances, clean baseline, Isolation Forest, risk and localization.
- `src/evaluation/`: executed multi-seed metrics and CLI.
- `src/dashboard/`, `app.py`: Azerbaijani dashboard.
- `tests/`: physics, controls, ranking, leakage, determinism, and AppTest smoke checks.
- `docs/demo_script.md`: live competition sequence.

## Future Utility Integration

Potential future inputs include AMI, feeder and transformer meters, SCADA, GIS, OMS, asset records, and inspection results. These are design concepts, not current connections. No automatic punitive action is proposed.

