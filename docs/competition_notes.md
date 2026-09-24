# Hard judge questions

**Your simulator creates the data, so aren't you detecting your own assumptions?** Yes, this is synthetic validation. V2 prevents the detector from knowing exact simulated R, V, power factor, sensor errors, or event labels. Multi-seed and clean-control results stress the method, but field accuracy requires independent utility data.

**Why is the clean residual not exactly zero?** True physical parameters differ from nominal detector assumptions, and independently noisy sensors vary. The clean median and spread are learned in a pre-event calibration window.

**Why use AI if energy balance finds the loss?** Feeder energy balance localizes an unexplained gap. Isolation Forest ranks unusual meter behavior for human review. It does not turn feeder evidence into customer proof.

**Can you identify the exact customer using bypass electricity?** No. A bypass load with normal meter readings supports feeder localization only. There is insufficient evidence to name a customer.

**What if line resistance is wrong?** The clean baseline absorbs modest systematic bias and a sigma floor reduces overreaction. Large topology or impedance errors could still invalidate alerts; field calibration is necessary.

**What if voltage varies?** The true simulator varies voltage slightly; the detector assumes nominal voltage. Larger real variation would require voltage telemetry or a broader calibrated baseline.

**What if a meter is inaccurate?** Modest independent noise is simulated. Systematic calibration errors can resemble energy loss and require meter testing before attribution.

**What if communication fails?** Missing reads are imputed from clean same-slot reference, marked as a quality issue, and excluded from physical-loss classification when substantial. The dashboard asks for telemetry checks.

**Is an anomaly score a theft probability?** No. Isolation Forest score measures behavioral distance from its clean training set. The combined risk score is a normalized prioritization index, not a probability.

**How do you avoid false accusations?** Feeder evidence and meter behavior remain distinct. Dropout and zero reporting have service/health labels. Persistence and data-quality gates limit one-day or missing-data alerts. Human investigation is required.

**Why Isolation Forest?** It needs no synthetic fraud labels for training, handles a small interpretable feature set, and is light enough for the demo. We calibrate its score against clean baseline samples.

**Why not deep learning?** Thirty synthetic customers and a short baseline do not justify a large model. Complexity would not create real-world evidence.

**How well does 10% under-reporting perform?** In the executed 10-seed V2 suite, it was detected in 0/10 runs. The 20% case was detected in 10/10 but only after an average 184.8 hours. The 30% and 40% cases were detected in 10/10 with 48-hour mean delay. These are synthetic results, not field guarantees.

**How many simulations were evaluated?** The configured full run uses 10 seeds × 9 scenarios = 90 simulation/detection runs, including 10 clean controls. The page shows the actual executed count; if fewer seeds are selected, it reports the smaller count.

**Are these real Azerishiq data?** No. Customer profiles, network parameters, measurements and events are synthetic. No direct Azerishiq connection exists.

**Can this integrate with existing infrastructure?** Future Utility Integration could ingest AMI, feeder and transformer meters, SCADA, GIS, OMS, asset records and inspection outcomes after data governance and mapping work. Current functionality is local synthetic simulation only.

**What is needed before a real pilot?** Verify topology and time alignment, calibrate line impedance and sensor accuracy, handle seasonal/weather/load shifts, secure AMI quality codes, measure outcomes against independent field inspections, tune thresholds with utility engineers, and require human review.

**What is the transformer layer?** Independently noisy transformer and feeder readings give a system-level conservation sanity check. It is not claimed as a separate theft detector.

**Can you automatically penalize a high-risk customer?** No. This is a decision support system. High score means inspection priority, never proof of misconduct or a basis for automatic punitive action.

