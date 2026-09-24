# Architecture

```mermaid
flowchart TD
    A[True network state: load, R, V, pf, temperature] --> B[Physical simulation]
    B --> C[True customer, unmetered and I²R energy]
    C --> D[Sensor and meter measurement layer]
    D --> E[Measured feeder and transformer inputs]
    D --> F[Reported smart-meter readings and quality flags]
    E --> G[Detector: nominal R, V and pf technical-loss estimate]
    F --> G
    G --> H[Energy-balance residual]
    H --> I[Clean statistical baseline and persistence]
    F --> J[Daily meter features]
    J --> K[Clean-baseline Isolation Forest]
    I --> L[Feeder risk and localization]
    K --> M[Meter inspection priority]
    L --> M
    M --> N[Human-readable explanation and dashboard]
    B --> T[Ground truth labels]
    T -. evaluation only .-> Q[Validation metrics]
    N -. predictions .-> Q
```

The detector reads only `Simulation.customers`, `meters`, `feeders`, `transformer`, and nominal config. The `physical_*` frames and `truth` frame are retained for energy-conservation tests and evaluation, and are never referenced in `detect()`.

Physical feeder input equals true customer load plus true unmetered load plus true feeder technical loss. Physical transformer input equals all true feeder inputs plus true transformer loss. Independent sensor noise changes the measured readings, not those conservation identities. Transformer residuals therefore vary under clean operation; they are presented as a system-level sanity check.

One feeder imbalance can identify the affected feeder. A bypass load with normal meter behavior cannot be assigned to a particular customer from these channels alone. Only a distinct meter pattern plus feeder context affects a customer's inspection priority.

