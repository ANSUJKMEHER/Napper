"""Synthetic demo datasets with planted storylines.

Everything the demo claims Napper catches is planted here, deterministically:
- bank.csv: a gym price hike (24.99 -> 29.99 in June), a forgotten monthly
  subscription ("Streamly"), and a double electricity charge on 2026-09-20.
- electricity.csv: a 3-day kWh spike (2026-09-14..16).
- steps.csv: a slow and steady upward trend (the theme, literally).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config

START = "2025-10-01"
PERIODS = 386  # through 2026-10-21


def _dates():
    return pd.date_range(START, periods=PERIODS, freq="D")


def bank_csv(path: Path) -> int:
    rng = np.random.default_rng(7)
    rows: list[dict] = []

    def add(d, desc, amt):
        rows.append({"date": d.strftime("%Y-%m-%d"), "description": desc, "amount": round(float(amt), 2)})

    for d in _dates():
        if d.day == 1:
            add(d, "ACME CORP PAYROLL", 6200.00)
        if d.day == 3:
            add(d, "OAK STREET APARTMENTS", -1450.00)
        if d.day == 5:
            add(d, "FITNESS FIRST GYM", -24.99 if d <= pd.Timestamp("2026-05-31") else -29.99)
        if d.day == 8:
            add(d, "NETFLIX.COM", -12.99)
        if d.day == 12:
            add(d, "STREAMLY SUBSCRIPTION", -9.99)  # the forgotten one
        if d.day == 20:
            base = 100 + 25 * np.sin(2 * np.pi * (d.month / 12)) + rng.normal(0, 8)
            add(d, "CITY POWER & LIGHT", -round(base, 2))
            if d == pd.Timestamp("2026-09-20"):
                add(d, "CITY POWER & LIGHT", -round(base, 2))  # double charge
    for d in _dates():
        if rng.random() < 0.45 and d.dayofweek < 5:
            add(d, "BLUEBIRD COFFEE", -round(4.5 + rng.normal(0, 0.7), 2))
        if d.dayofweek == 5 and rng.random() < 0.9:
            add(d, "GREENBASKET GROCERY", -round(70 + rng.normal(0, 22), 2))
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    df.to_csv(path, index=False)
    return len(df)


def electricity_csv(path: Path) -> int:
    rng = np.random.default_rng(62)  # seed chosen so the only screen flags are the planted spike
    d = _dates()
    seasonal = 8 * np.sin(2 * np.pi * (d.dayofyear - 15) / 365)
    winter = np.where(d.month.isin([12, 1, 2]), 7.0, 0.0)
    weekend = np.where(d.dayofweek >= 5, -3.0, 0.0)
    spike = np.where((d >= pd.Timestamp("2026-09-14")) & (d <= pd.Timestamp("2026-09-16")), 45.0, 0.0)
    kwh = 22 + seasonal + winter + weekend + spike + rng.normal(0, 2.2, len(d))
    pd.DataFrame({"date": d.strftime("%Y-%m-%d"), "kwh": np.round(kwh, 1)}).to_csv(path, index=False)
    return len(d)


def steps_csv(path: Path) -> int:
    rng = np.random.default_rng(64)  # seed chosen so the screen stays quiet on the demo data
    d = _dates()
    trend = np.linspace(0, 1400, len(d))  # slow and steady
    weekend = np.where(d.dayofweek >= 5, -1500.0, 0.0)
    steps = 6800 + trend + weekend + rng.normal(0, 1100, len(d))
    pd.DataFrame({"date": d.strftime("%Y-%m-%d"), "steps": np.round(steps).astype(int)}).to_csv(path, index=False)
    return len(d)


def generate_all() -> dict[str, int]:
    config.INBOX.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for name, fn in (("bank", bank_csv), ("electricity", electricity_csv), ("steps", steps_csv)):
        p = config.INBOX / f"{name}.csv"
        fn(p)
        counts[name] = len(pd.read_csv(p))
    return counts
