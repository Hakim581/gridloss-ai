"""Export the deterministic scenario and detector outputs as CSV."""

from pathlib import Path

from src.detection.localization import detect
from src.simulation.simulator import simulate


def main():
    output = Path("data/generated")
    output.mkdir(parents=True, exist_ok=True)
    sim = simulate()
    result = detect(sim)
    for name, frame in {
        "customers": sim.customers, "meters": sim.meters, "feeders": sim.feeders,
        "transformer": sim.transformer, "scenario_truth": sim.truth,
        "feeder_daily": result.feeder_daily, "meter_daily": result.meter_daily,
        "feeder_summary": result.feeder_summary, "meter_summary": result.meter_summary,
    }.items():
        frame.to_csv(output / f"{name}.csv", index=False)
    print(f"Wrote nine CSV files to {output.resolve()}")


if __name__ == "__main__":
    main()
