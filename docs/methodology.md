# Engineering method and limitations

At each 15-minute interval, the feeder residual is

`unexplained = feeder input − reported meter energy − estimated missing meter energy − expected technical loss`.

The feeder loss estimate is `3 I²R Δt`, where `I = P/(√3 V pf)`. `P` uses accounted meter energy; consequently an unmetered load can also increase actual I²R beyond the estimate. Transformer loss is core loss plus a quadratic copper term and is checked independently. These are simplified balanced three-phase estimates, not power-flow calculations.

Missing meter reads are imputed from that meter's median in the same 15-minute slot during the first ten clean days. A missing-read flag remains visible. Zero reads are treated separately because they may reflect meter failure. An operator should verify telemetry and physical meter condition before interpreting an energy residual.

Daily feeder residuals are compared to a clean ten-day baseline. The risk score combines residual deviation (standard deviations) and the ratio of unexplained energy to expected technical loss. Isolation Forest is trained only on baseline daily meter features: consumption relative to baseline, zero fraction, and missing fraction. The model score is one contribution to a transparent meter inspection score, alongside consumption drop and feeder context. Thresholds are demonstration settings in `risk_scoring.py`, not utility-calibrated probabilities. A risk score is not a confidence probability.

Feeder onset is the first post-baseline day reaching Medium Risk. Reported energy, technical loss, missing estimates, and unexplained energy are shown separately so an engineer can audit the result. The synthetic evaluation reports feeder-day precision and recall against known events; real-world performance requires representative utility data, calibration of impedances and sensor errors, seasonal baselines, and field validation.
