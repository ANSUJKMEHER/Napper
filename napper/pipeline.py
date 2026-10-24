"""The overnight run: ingest -> series -> forecast -> anomalies -> digest."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from . import config, digest, forecast as fc, ingest, recurring, tracing


def discover_columns(df: pd.DataFrame):
    """Guess date / text / numeric columns of a normalized dataset."""
    date_col = None
    for c in df.columns:
        if c in config.DATE_COLUMN_NAMES:
            date_col = c
            break
    if date_col is None:
        for c in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[c]):
                date_col = c
                break
    text_cols = [c for c in df.columns if c != date_col and pd.api.types.is_string_dtype(df[c])]
    num_cols = [c for c in df.columns if c != date_col and pd.api.types.is_numeric_dtype(df[c])]
    return date_col, text_cols, num_cols


def build_series(df: pd.DataFrame, date_col, text_cols, num_cols, dataset: str, engine: str = "auto") -> list[dict]:
    """Forecast series per dataset.

    Bank-like data (text descriptions + an amount column) forecasts monthly
    spend, which keeps the holdout metrics sane. Its anomaly screen is off:
    monthly bills drift across weekdays, which breaks same-weekday screens.
    Recurring + duplicate detectors cover that ground instead. Generic CSVs
    (kwh, steps) get a daily series with the walk-forward screen on.
    """
    series: list[dict] = []
    d = df.copy()
    d["_dt"] = pd.to_datetime(d[date_col])
    amount_col = next(
        (c for c in num_cols if "amount" in c.lower() or "debit" in c.lower() or c.lower() == "amt"),
        None,
    )
    if amount_col is not None and text_cols:
        amt = pd.to_numeric(d[amount_col], errors="coerce")
        spend = amt.where(amt < 0, 0.0).abs()
        daily = spend.groupby(d["_dt"]).sum()
        monthly = daily.resample("ME").sum()
        # drop an incomplete final month so the holdout compares full months
        if len(monthly) > 1:
            start = monthly.index[-1].to_period("M").start_time
            coverage = (d["_dt"].max() - start).days + 1
            if coverage < 28:
                monthly = monthly.iloc[:-1]
        series.append(
            {
                "name": f"{dataset}:spend",
                "df": pd.DataFrame({"date": monthly.index, "value": monthly.values}),
                "unit": amount_col,
                "horizon_periods": 1,  # next month
                "holdout_periods": 1,  # vs the previous full month
                "step_days": 30,
                "period_lag": 1,
                "skip_anomaly_screen": True,
            }
        )
        # daily diagnostic: only meaningful with the real TabPFN engine, which
        # can learn day-of-month patterns (rent day etc.) that the naive
        # baseline cannot. Skipped when tabpfn is not installed or in fast mode.
        if fc.has_tabpfn() and engine not in ("naive", "fast"):
            g = daily.asfreq("D").fillna(0.0)
            series.append(
                {
                    "name": f"{dataset}:spend-daily",
                    "df": pd.DataFrame({"date": g.index, "value": g.values}),
                    "unit": amount_col,
                    "skip_anomaly_screen": True,
                    "diagnostic": True,
                }
            )
        num_cols = [c for c in num_cols if c != amount_col]
    for col in num_cols:
        g = d.groupby("_dt")[col].sum().asfreq("D").fillna(0.0)
        series.append(
            {
                "name": f"{dataset}:{col}",
                "df": pd.DataFrame({"date": g.index, "value": g.values}),
                "unit": col,
            }
        )
    return series


def run(engine: str = "auto") -> dict:
    tracing.init_tracing()
    t0 = datetime.now()

    with tracing.trace_step("ai.agent", f"napper.run:{engine}"):
        with tracing.trace_step("ai.tool.ingest", "ingest_inbox_csvs", data={"inbox": str(config.INBOX)}):
            imported = ingest.ingest_all()

        summary: dict = {
            "imported": imported,
            "series": [],
            "events": [],
            "digest": None,
            "digest_writer": "template",
            "engine": engine,
        }

        for store in sorted(config.STORE.glob("*.csv")):
            try:
                df = pd.read_csv(store, encoding="utf-8-sig")
            except Exception as exc:
                summary["events"].append({"type": "error", "message": f"{store.name}: {exc}"})
                continue
            date_col, text_cols, num_cols = discover_columns(df)
            if date_col is None:
                summary["events"].append({"type": "error", "message": f"{store.name}: no date column found"})
                continue
            dataset = store.stem
            if text_cols:
                amt_candidates = [c for c in num_cols if "amount" in c.lower() or "debit" in c.lower()]
                amt_candidates = amt_candidates or ["amount"]
                with tracing.trace_step("ai.tool.recurring", f"detect_recurring:{store.name}"):
                    try:
                        table, events = recurring.detect_recurring(df, date_col, text_cols[0], amt_candidates[0])
                        summary["recurring"] = table
                        summary["events"].extend(events)
                    except Exception as exc:
                        summary["events"].append({"type": "error", "message": f"{store.name} recurring: {exc}"})
                with tracing.trace_step("ai.tool.duplicate", f"detect_duplicates:{store.name}"):
                    try:
                        summary["events"].extend(
                            recurring.detect_duplicate_charges(df, date_col, text_cols[0], amt_candidates[0])
                        )
                    except Exception as exc:
                        summary["events"].append({"type": "error", "message": f"{store.name} duplicates: {exc}"})
            for spec in build_series(df, date_col, text_cols, num_cols, dataset, engine=engine):
                result: dict = {"name": spec["name"], "unit": spec["unit"]}
                try:
                    with tracing.trace_step(
                        "ai.pipeline.forecast_series",
                        f"forecast:{spec['name']}",
                        data={"series": spec["name"], "unit": spec["unit"], "engine": engine},
                    ):
                        result.update(
                            fc.forecast(
                                spec["df"],
                                horizon_periods=spec.get("horizon_periods", config.FORECAST_HORIZON_DAYS),
                                holdout_periods=spec.get("holdout_periods", config.HOLDOUT_DAYS),
                                step_days=spec.get("step_days", 1),
                                period_lag=spec.get("period_lag", 7),
                                anomaly_screen=not spec.get("skip_anomaly_screen", False),
                                engine=engine,
                            )
                        )
                except Exception as exc:
                    result["error"] = str(exc)
                summary["series"].append(result)

        context = {
            "date": date.today().isoformat(),
            "forecasts": [s for s in summary["series"] if "next_sum" in s],
            "events": summary["events"],
        }
        with tracing.trace_step("ai.pipeline.digest", "generate_digest"):
            text = digest.gemma_digest(digest.build_prompt(context))
            if text is None:
                text = digest.template_digest(context)
            else:
                summary["digest_writer"] = "gemma (local ollama)"
            summary["digest"] = text
            summary["digest_file"] = str(digest.write_digest(text))

        tracing.record_cost_metric(0.0)

    config.FORECASTS.mkdir(parents=True, exist_ok=True)
    stamp = t0.strftime("%Y%m%d-%H%M%S")
    (config.FORECASTS / f"run-{stamp}.json").write_text(json.dumps(summary, indent=2, default=str))
    summary["elapsed_seconds"] = round((datetime.now() - t0).total_seconds(), 1)
    return summary
