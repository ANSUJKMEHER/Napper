"""Forecasting.

Primary engine: TabPFN-3.5 (open-weight, local, `pip install tabpfn`).
Fallback: linear-detrended naive baseline, so the pipeline runs on any machine.

A tabular foundation model sees a time series as rows of calendar + lag
features. The horizon is produced by recursive one-step prediction, stepping
`step_days` per period (1 = daily series, 7 = weekly series). The naive
baseline is always computed, so every run carries its own comparison point.
"""

from __future__ import annotations

import functools
import time

import numpy as np
import pandas as pd

from . import anomaly, config, tracing

LAGS = (1, 2, 7, 14, 30)
FEATURE_COLS = [
    "dow",
    "day",
    "month",
    "doy",
    *[f"lag_{lag}" for lag in LAGS],
    "roll7",
    "roll30",
    "trend",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar + lag features. Expects columns date, value."""
    d = df.copy().sort_values("date").reset_index(drop=True)
    d["dow"] = d["date"].dt.dayofweek
    d["day"] = d["date"].dt.day
    d["month"] = d["date"].dt.month
    d["doy"] = d["date"].dt.dayofyear
    v = d["value"]
    for lag in LAGS:
        d[f"lag_{lag}"] = v.shift(lag)
    d["roll7"] = v.shift(1).rolling(7, min_periods=1).mean()
    d["roll30"] = v.shift(1).rolling(30, min_periods=1).mean()
    d["trend"] = np.arange(len(d)) / max(len(d) - 1, 1)
    return d


def has_tabpfn() -> bool:
    """True when the local TabPFN package is importable."""
    try:
        import tabpfn  # noqa: F401
        return True
    except ImportError:
        return False


def naive_predict(history: np.ndarray, horizon: int) -> np.ndarray:
    """Linear-detrended naive: last month's mean plus the recent slope."""
    recent = history[-30:]
    x = np.arange(len(recent), dtype=float)
    slope = float(np.polyfit(x, recent, 1)[0]) if len(recent) > 2 else 0.0
    base = float(recent.mean())
    return np.array([base + slope * (i + 1) for i in range(horizon)])


def _next_row(prev_row: pd.Series, new_date, new_value: float, hist: np.ndarray) -> pd.DataFrame:
    row = {
        "date": new_date,
        "value": new_value,
        "dow": new_date.dayofweek,
        "day": new_date.day,
        "month": new_date.month,
        "doy": new_date.dayofyear,
        "trend": float(prev_row["trend"]) + 1.0 / max(len(hist) + 1, 1),
    }
    for lag in LAGS:
        idx = len(hist) - lag
        row[f"lag_{lag}"] = float(hist[idx]) if idx >= 0 else np.nan
    row["roll7"] = float(np.mean(hist[-7:]))
    row["roll30"] = float(np.mean(hist[-30:]))
    return pd.DataFrame([row])


def _recursive_forecast(model, last_row: pd.Series, hist: np.ndarray, horizon: int, step_days: int) -> np.ndarray:
    """One-step-ahead recursion, feeding predictions back as lags."""
    preds: list[float] = []
    current = last_row.to_frame().T
    date = pd.Timestamp(current["date"].iloc[-1])
    for _ in range(horizon):
        date = date + pd.Timedelta(days=step_days)
        x = current[FEATURE_COLS].iloc[[-1]]
        p = float(np.asarray(model.predict(x)).ravel()[0])
        preds.append(p)
        current = _next_row(current.iloc[-1], date, p, hist)
        hist = np.append(hist, p)
    return np.array(preds)


def _metrics(actual, pred):
    a = np.asarray(actual, dtype=float)
    p = np.asarray(pred, dtype=float)
    if len(a) == 0:
        return None, None, None
    wmape = float(np.sum(np.abs(a - p)) / max(np.sum(np.abs(a)), 1e-9) * 100)
    rmse = float(np.sqrt(np.mean((a - p) ** 2)))
    mape = None
    if not np.all(a == 0):
        with np.errstate(divide="ignore", invalid="ignore"):
            mape = float(np.nanmean(np.abs((a - p) / np.where(a == 0, np.nan, a))) * 100)
    return wmape, mape, rmse


def seasonal_expected(values: np.ndarray, i: int, period_lag: int) -> float | None:
    """Mean of the same season over the previous 4 periods.

    period_lag=7: same weekday in prior weeks (daily series).
    period_lag=1: prior weeks (weekly series).
    """
    pts = [float(values[i - period_lag * k]) for k in range(1, 9) if i - period_lag * k >= 0]
    if not pts:
        return None
    # Median, not mean: a couple of bad weeks must not poison the expectation.
    return float(np.median(pts))


def walk_forward_anomalies(
    d: pd.DataFrame,
    window_periods: int = config.WALK_FORWARD_WINDOW_DAYS,
    period_lag: int = 7,
) -> list[dict]:
    """Rolling screen: expected = same season in prior periods.

    Catches planted events near the end of a series (spikes, one-off jumps)
    without labels and without a model.
    """
    with tracing.trace_step(
        "ai.tool.anomaly_screen",
        "walk_forward_seasonal_screen",
        data={"window_periods": window_periods, "period_lag": period_lag, "data_points": len(d)},
    ):
        values = d["value"].to_numpy(dtype=float)
        dates = d["date"].dt.strftime("%Y-%m-%d").tolist()
        start = max(len(d) - window_periods, 8 * period_lag)
        flags: list[dict] = []
        for i in range(start, len(d)):
            exp = seasonal_expected(values, i, period_lag)
            if exp is None:
                continue
            flags.extend(
                anomaly.flag_points(
                    [dates[i]],
                    [values[i]],
                    [exp],
                    sigma=3.0,
                    min_pct=config.WALK_FORWARD_MIN_PCT,
                )
            )
        return flags


def forecast(
    df: pd.DataFrame,
    horizon_periods: int = config.FORECAST_HORIZON_DAYS,
    holdout_periods: int = config.HOLDOUT_DAYS,
    step_days: int = 1,
    period_lag: int = 7,
    anomaly_screen: bool = True,
) -> dict:
    """Forecast a series (columns date, value). Returns a json-safe dict.

    step_days=1, period_lag=7 -> daily series; step_days=7, period_lag=1 -> weekly.
    """
    d = df[["date", "value"]].copy()
    d["date"] = pd.to_datetime(d["date"])
    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    d = d.sort_values("date").dropna().reset_index(drop=True)
    min_points = max(4 * period_lag + 2, 2 * holdout_periods + 8)
    if len(d) < min_points:
        return {"error": f"need >= {min_points} points, got {len(d)}"}

    feat = build_features(d)
    n = len(d) - holdout_periods
    train_feat = feat.iloc[:n]
    test_feat = feat.iloc[n:]
    test_actual = d["value"].to_numpy()[n:]
    test_dates = d["date"].iloc[n:].dt.strftime("%Y-%m-%d").tolist()
    hist = d["value"].to_numpy(dtype=float)

    model_name = "naive-baseline"
    elapsed = 0.0
    test_pred = None
    horizon = None
    naive_test = naive_predict(hist[:n], len(test_actual))
    naive_horizon = naive_predict(hist, horizon_periods)

    try:
        from tabpfn import TabPFNRegressor  # optional, heavy

        reg = TabPFNRegressor(device="auto")
        t0 = time.perf_counter()
        with tracing.trace_step(
            "ai.model.tabpfn",
            "tabpfn_3_5_forecast",
            data={
                "n_features": len(FEATURE_COLS),
                "n_train": n,
                "horizon_periods": horizon_periods,
                "model": "tabpfn-3.5",
            },
        ):
            reg.fit(train_feat[FEATURE_COLS], hist[:n])
            test_pred = np.asarray(reg.predict(test_feat[FEATURE_COLS])).ravel()
            horizon = _recursive_forecast(reg, feat.iloc[-1], hist, horizon_periods, step_days)
        model_name = "tabpfn-3.5"
        elapsed = round(time.perf_counter() - t0, 2)
    except ImportError:
        pass  # tabpfn not installed; naive fallback
    except Exception as exc:  # keep the pipeline alive on model hiccups
        model_name = f"tabpfn-error({type(exc).__name__})"

    if test_pred is None:
        test_pred = naive_test
    if horizon is None:
        horizon = naive_horizon

    wmape, mape, rmse = _metrics(test_actual, test_pred)
    nwmape, nmape, nrmse = _metrics(test_actual, naive_test)
    holdout_flags = anomaly.flag_points(test_dates, test_actual, test_pred) if anomaly_screen else []
    history_flags = (
        walk_forward_anomalies(d, period_lag=period_lag) if anomaly_screen else []
    )

    last_date = d["date"].iloc[-1]
    dates_out = [
        (last_date + pd.Timedelta(days=(i + 1) * step_days)).strftime("%Y-%m-%d")
        for i in range(horizon_periods)
    ]
    return {
        "model": model_name,
        "train_points": int(n),
        "holdout_points": int(len(test_actual)),
        "horizon_periods": int(horizon_periods),
        "step_days": int(step_days),
        "wmape_pct": round(wmape, 2) if wmape is not None else None,
        "mape_pct": round(mape, 2) if mape is not None else None,
        "rmse": round(rmse, 2) if rmse is not None else None,
        "baseline": {
            "model": "linear-naive",
            "wmape_pct": round(nwmape, 2) if nwmape is not None else None,
            "mape_pct": round(nmape, 2) if nmape is not None else None,
            "rmse": round(nrmse, 2) if nrmse is not None else None,
        },
        "fit_seconds": elapsed,
        "next_sum": round(float(np.sum(horizon)), 2),
        "next_avg": round(float(np.mean(horizon)), 2),
        "pred": [
            {"date": dates_out[i], "value": round(float(horizon[i]), 2)} for i in range(horizon_periods)
        ],
        "anomalies": holdout_flags,
        "history_anomalies": history_flags,
    }
