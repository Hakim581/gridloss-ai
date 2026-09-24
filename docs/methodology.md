# Engineering and evaluation methodology

## Physical and observed layers

At each 15-minute interval the hidden simulator computes

`E_f,true = E_customers,true + E_unmetered,true + 3 I_true² R(T) Δt / 1000`,

where `I_true = P / (√3 V_true pf_true)` and `R(T)=R_ref[1+α(T−T_ref)]`. Synthetic seven-day conductor-temperature variation, daily voltage variation, and three-day power-factor variation are configured in `network_truth`. These are plausible prototype assumptions, **not actual Azerishiq line parameters** and not a full three-phase power-flow model.

The measurement layer independently perturbs customer meter energy, feeder input energy, and transformer input energy with zero-mean relative Gaussian noise, clips impossible negative readings, and rounds to the configured precision. Under-reporting changes the reported smart-meter channel while physical load remains unchanged. Unmetered load increases physical feeder load without adding a smart-meter reading. Meter failure reports zero; dropout reports missing; legitimate high consumption increases physical and reported consumption together.

The detector uses `detector_assumptions` for nominal R, V, power factor and transformer loss coefficients. Its feeder residual is

`measured feeder input − reported customer energy − imputed missing energy − estimated I²R loss`.

It never reads true physical columns or event labels. Clean residuals are small and variable because model parameters and sensor readings differ. A nonzero clean center is calibrated rather than treated as theft. The transformer balance compares independently noisy measured transformer and feeder channels and is only a system-level check.

## Baseline and alerts

The first ten days are a **clean pre-event calibration window**. The simulator rejects incident starts inside this window. For missing meter intervals, the detector uses the same customer's same-quarter-hour median from this clean window; missing status remains explicit. Daily meter consumption references use separate weekday and weekend medians.

For each feeder, baseline daily residual median and standard deviation are calculated from clean days. The standard deviation has a floor proportional to expected technical loss so a very stable synthetic baseline does not produce exaggerated z-scores. The positive excess above baseline center supplies two configured components: normalized statistical deviation and normalized excess/expected-loss ratio. A feeder alert requires two consecutive days above the configured medium threshold. Days with substantial missing telemetry are excluded from physical-loss alerts.

The meter index combines configured consumption-drop, Isolation Forest behavioral anomaly, and confirmed feeder context weights. It is an inspection priority index in [0,1]. Config validation requires each weight group to sum to one and bands to be ordered. The score is **not** a probability of theft.

## Isolation Forest and leakage

Isolation Forest is trained only on clean baseline daily rows. Features are limited to consumption/reference ratio, zero-read fraction, and missing-read fraction. Baseline scores establish a configurable upper quantile; the normalized score is an anomaly index, not a probability. Random state is fixed by the simulation seed. No truth label enters feature engineering, fitting, balance, or scoring. The baseline window is retrospective: post-baseline alerts never use future anomalous observations. Event labels enter only `src/evaluation/metrics.py` after detection.

The default contamination is a training hyperparameter, not the asserted fraction of fraudulent customers. Risk weights and thresholds are hand-tuned demonstration settings. They need field calibration before utility use. One-day spikes are deliberately insufficient for a feeder alert.

## Executed validation definitions

Each configured seed runs nine scenarios: clean; four under-reporting severities; unmetered load; meter failure; dropout; and legitimate high consumption. Evaluation uses only post-baseline feeder-days. Under-reporting, unmetered load, and meter failure define positive feeder-days; clean, dropout and legitimate high consumption define negative feeder-days.

- Precision = true-positive alerted feeder-days / all alerted feeder-days.
- Recall = true-positive alerted feeder-days / all positive feeder-days.
- F1 = harmonic mean of precision and recall.
- False-positive rate = false-positive alerted feeder-days / all true-negative feeder-days, including clean controls.
- Localization accuracy = physical-event scenarios where the highest-risk feeder equals the injected feeder **and** a qualifying alert occurred / all physical-event scenarios.
- Detection delay = first qualifying daily alert's availability time (next midnight) minus event start. Undetected events have missing delay and are counted separately; the reported average covers detected physical events only.
- Customer top-three accuracy applies only to under-reporting and is an inspection-ranking measure, not exact-cause proof.

Feeder-day metrics and event-level metrics answer different questions. Low-severity events may remain undetected; the evaluation reports that honestly. The synthetic data distribution and injected anomalies are known, so these values cannot be claimed as field accuracy.

## Responsible interpretation

Communication dropout is a data-quality problem. A zero-reporting meter merits a health check, not a root-cause declaration. A normal meter on a feeder with unmetered load receives no customer-level attribution. Engineers should verify topology, meter condition, telemetry, and legitimate usage before any field action. No automated punitive action follows from a score.
