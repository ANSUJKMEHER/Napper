"""Explainable anomaly detection: residuals vs a robust band."""

from __future__ import annotations

import numpy as np

from . import config


def robust_sigma(values: np.ndarray) -> float:
    """MAD-based sigma (robust to outliers). Falls back to std when MAD is zero."""
    med = float(np.median(values))
    mad = float(np.median(np.abs(values - med)))
    sigma = mad * 1.4826
    return sigma if sigma > 1e-9 else float(np.std(values))


def flag_points(
    dates,
    actual,
    expected,
    sigma: float = config.ANOMALY_SIGMA,
    min_pct: float = config.ANOMALY_MIN_PCT,
) -> list[dict]:
    """Flag points where actual strays from expected beyond the robust band.

    dates: list[str]; actual/expected: array-likes. Returns json-safe dicts.
    """
    a = np.asarray(actual, dtype=float)
    e = np.asarray(expected, dtype=float)
    resid = a - e
    scale = robust_sigma(resid) or 1.0
    out: list[dict] = []
    for i in range(len(a)):
        if abs(resid[i]) > sigma * scale:
            if abs(e[i]) < 1e-9:
                out.append(
                    {
                        "date": str(dates[i]),
                        "actual": round(float(a[i]), 2),
                        "expected": round(float(e[i]), 2),
                        "off_pct": None,
                        "note": f"{dates[i]}: {a[i]:.2f} on a usually-flat day (expected ~{e[i]:.2f})",
                    }
                )
                continue
            pct = abs(resid[i]) / abs(e[i]) * 100.0
            if pct >= min_pct:
                out.append(
                    {
                        "date": str(dates[i]),
                        "actual": round(float(a[i]), 2),
                        "expected": round(float(e[i]), 2),
                        "off_pct": round(pct, 1),
                        "note": f"{dates[i]}: {a[i]:.2f} vs expected {e[i]:.2f} ({pct:+.0f}%)",
                    }
                )
    return out
