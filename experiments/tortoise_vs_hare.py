#!/usr/bin/env python3
"""Tortoise vs Hare: the closed-vs-open comparison table for the write-up.

Tortoise: Napper's local stack. Open TabPFN-3.5 weights, data never leaves
the machine, $0 per run, works in airplane mode.
Hare: a closed hosted forecasting API you would pay for.

The hare numbers are placeholders on purpose. Do NOT invent them for the
post: plug in your real closed API, measure it, then fill the table.
Usage: python -m experiments.tortoise_vs_hare [--data data/store/bank.csv]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from napper import config, forecast as fc, pipeline  # noqa: E402


def hare_forecast(series, key=None):
    """Closed hosted API placeholder. Implement with a real API before posting."""
    if not key:
        raise NotImplementedError(
            "Pass --hare-key and implement hare_forecast() with the closed API you "
            "want to compare against. Leave it unimplemented until you have real numbers."
        )
    raise NotImplementedError("Implement the closed API call; return (predictions, cost_usd, latency_s).")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Closed-vs-open comparison table.")
    ap.add_argument("--data", default="data/store/bank.csv", help="stored dataset CSV")
    ap.add_argument("--hare-key", default=None, help="closed API key (optional, see hare_forecast)")
    args = ap.parse_args(argv)

    store = Path(args.data)
    if not store.exists():
        print(f"missing {store}; run `python -m napper.cli demo` first")
        return 1

    df = pd.read_csv(store)
    date_col, text_cols, num_cols = pipeline.discover_columns(df)
    specs = pipeline.build_series(df, date_col, text_cols, num_cols, store.stem)
    # Prefer the daily diagnostic (where the open model earns its keep);
    # fall back to the monthly spend series.
    spec = next(
        (s for s in specs if s["name"].endswith(":spend-daily")),
        next((s for s in specs if s["name"].endswith(":spend")), specs[0]),
    )

    t0 = time.perf_counter()
    result = fc.forecast(
        spec["df"],
        horizon_periods=spec.get("horizon_periods", config.FORECAST_HORIZON_DAYS),
        holdout_periods=spec.get("holdout_periods", config.HOLDOUT_DAYS),
        step_days=spec.get("step_days", 1),
        period_lag=spec.get("period_lag", 7),
        anomaly_screen=not spec.get("skip_anomaly_screen", False),
    )
    tortoise_latency = time.perf_counter() - t0
    engine = result.get("model", "?")
    wmape = result.get("wmape_pct")
    baseline = result.get("baseline", {})

    table = "\n".join(
        [
            "| | Hare (closed hosted API) | Tortoise (Napper, local) |",
            "|---|---|---|",
            "| Model | {{fill: your closed API}} | %s (open weights) |" % engine,
            "| Cost per run | {{fill: your real API bill}} | $0.00 |",
            "| Data leaves the machine | yes | no |",
            "| Works offline / airplane mode | no | yes |",
            "| Holdout error (WMAPE) | {{fill: your real number}} | %s%% |" % wmape,
            "| Holdout error vs naive baseline | {{fill}} | baseline %s%% |" % baseline.get("wmape_pct"),
            "| Latency | {{fill}} | %.2fs |" % tortoise_latency,
            "| You can swap or audit the model | no | yes |",
            "",
        ]
    )
    print(table)
    config.OUT.mkdir(parents=True, exist_ok=True)
    out = config.OUT / "tortoise_vs_hare.md"
    out.write_text("# Tortoise vs Hare\n\n" + table, encoding="utf-8")
    print(f"Saved to {out}")

    if args.hare_key:
        hare_forecast(spec["df"], args.hare_key)  # raises until implemented
    return 0


if __name__ == "__main__":
    sys.exit(main())
