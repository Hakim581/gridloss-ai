"""Run the full reproducible synthetic validation on demand."""

import argparse
import json
from pathlib import Path

from .metrics import evaluate_suite


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", help="Override configured seeds")
    parser.add_argument("--output", type=Path, default=Path("data/generated"))
    args = parser.parse_args()
    summary, by_scenario, runs = evaluate_suite(seeds=args.seeds)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "evaluation_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8"
    )
    by_scenario.to_csv(args.output / "evaluation_by_scenario.csv", index=False)
    runs.to_csv(args.output / "evaluation_runs.csv", index=False)
    print(json.dumps(summary, indent=2, allow_nan=False))
    print(by_scenario.to_string(index=False))


if __name__ == "__main__":
    main()

