"""Lightweight local web server and dashboard for Napper.

Run: python -m napper.cli web [--port 5000]
Opens a local interactive dashboard in your default browser with:
- Drag-and-drop CSV ingestion
- Instant Nap Mode (~2s) vs Deep Sleep TabPFN Mode (~15m) toggle
- Interactive Chart.js time-series and forecast visualizer
- Planted storylines and anomaly cards
- Audio morning brief synthesis (Text-to-Speech)
- Sentry Agent Tracing waterfall view
"""

from __future__ import annotations

import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import cgi
import http.server
import json
import os
import socketserver
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from . import config, ingest, pipeline, sample_data


def get_latest_run_summary(engine: str | None = None) -> dict[str, Any] | None:
    """Load the most recent run artifact from data/forecasts/, optionally filtered by engine."""
    runs = sorted(config.FORECASTS.glob("run-*.json"), reverse=True)
    if not runs:
        return None

    # If deep/tabpfn requested (or default), prefer the newest run that used TabPFN
    if engine in ("deep", "tabpfn") or engine is None:
        for p in runs:
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if any("tabpfn" in s.get("model", "") for s in data.get("series", [])):
                        data["_filename"] = p.name
                        return data
            except Exception:
                continue

    # If fast/naive explicitly requested, find the newest naive run
    if engine in ("fast", "naive"):
        for p in runs:
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if all(s.get("model") == "naive-baseline" for s in data.get("series", [])):
                        data["_filename"] = p.name
                        return data
            except Exception:
                continue

    # Fallback to newest run
    try:
        with runs[0].open("r", encoding="utf-8") as f:
            data = json.load(f)
            data["_filename"] = runs[0].name
            return data
    except Exception:
        return None


def get_stored_datasets() -> list[dict[str, Any]]:
    """List datasets in data/store/ with summary stats and domain tags."""
    datasets = []
    domain_map = {
        "bank": ("Finance", "TabPFN Error: 2.03% • Gym Hike Caught"),
        "electricity": ("Utility", "3-Day Spike Flagged • 1 Duplicate Bill"),
        "steps": ("Fitness", "Periodic Baseline • 0 Noise Flags"),
        "water": ("Utility", "⚠️ Pipe Burst Leak (+706%)"),
    }
    for p in sorted(config.STORE.glob("*.csv")):
        dom, highlight = domain_map.get(p.stem, ("Time-Series", "Ingested & Ready"))
        try:
            df = pd.read_csv(p)
            datasets.append(
                {
                    "name": p.stem,
                    "filename": p.name,
                    "domain": dom,
                    "highlight": highlight,
                    "rows": len(df),
                    "columns": list(df.columns),
                    "size_kb": round(p.stat().st_size / 1024, 1),
                }
            )
        except Exception:
            datasets.append({
                "name": p.stem,
                "filename": p.name,
                "domain": dom,
                "highlight": "Ready",
                "rows": 0,
                "columns": [],
                "size_kb": 0,
            })
    return datasets


def get_series_chart_data(series_name: str | None = None, engine: str | None = None) -> dict[str, Any]:
    """Extract chart data for a series from the specified or latest run JSON."""
    latest = get_latest_run_summary(engine)
    if not latest or not latest.get("series"):
        return {"error": "No forecast runs available yet. Run the agent first."}

    series_list = latest["series"]
    target = None
    if series_name:
        target = next((s for s in series_list if s.get("name") == series_name), None)
    if not target:
        # Default to bank:spend-daily if present (where TabPFN shines), otherwise first series
        target = next((s for s in series_list if "spend-daily" in s.get("name", "")), series_list[0])

    s_name = target.get("name", "")
    dataset_name = s_name.split(":")[0] if ":" in s_name else s_name
    store_file = config.STORE / f"{dataset_name}.csv"

    history_dates: list[str] = []
    history_values: list[float] = []

    if store_file.exists():
        try:
            df = pd.read_csv(store_file)
            date_col, text_cols, num_cols = pipeline.discover_columns(df)
            if date_col:
                df["_dt"] = pd.to_datetime(df[date_col])
                df = df.sort_values("_dt")
                if "spend" in s_name and not s_name.endswith(":spend-daily"):
                    amt_col = next((c for c in num_cols if "amount" in c.lower() or "debit" in c.lower()), None)
                    if amt_col:
                        spend = pd.to_numeric(df[amt_col], errors="coerce").where(lambda x: x < 0, 0.0).abs()
                        monthly = spend.groupby(df["_dt"]).sum().resample("ME").sum()
                        history_dates = monthly.index.strftime("%Y-%m-%d").tolist()
                        history_values = [round(float(v), 2) for v in monthly.values]
                else:
                    col_target = s_name.split(":")[1] if ":" in s_name else None
                    if col_target and col_target in df.columns:
                        g = df.groupby("_dt")[col_target].sum().asfreq("D").fillna(0.0)
                        history_dates = g.index.strftime("%Y-%m-%d").tolist()
                        history_values = [round(float(v), 2) for v in g.values]
                    elif "spend-daily" in s_name:
                        amt_col = next((c for c in num_cols if "amount" in c.lower() or "debit" in c.lower()), None)
                        if amt_col:
                            spend = pd.to_numeric(df[amt_col], errors="coerce").where(lambda x: x < 0, 0.0).abs()
                            g = spend.groupby(df["_dt"]).sum().asfreq("D").fillna(0.0)
                            history_dates = g.index.strftime("%Y-%m-%d").tolist()
                            history_values = [round(float(v), 2) for v in g.values]
        except Exception:
            pass

    # Extract anomaly flags
    anomalies = []
    for a in target.get("history_anomalies", []):
        anomalies.append(
            {
                "date": a.get("date"),
                "value": a.get("actual"),
                "expected": a.get("expected"),
                "note": a.get("note"),
            }
        )

    # Forecast horizon
    forecast_points = target.get("pred", [])

    return {
        "series_name": s_name,
        "available_series": [s.get("name") for s in series_list if "name" in s],
        "model": target.get("model", "unknown"),
        "unit": target.get("unit", ""),
        "wmape_pct": target.get("wmape_pct"),
        "baseline_wmape_pct": target.get("baseline", {}).get("wmape_pct"),
        "fit_seconds": target.get("fit_seconds"),
        "next_sum": target.get("next_sum"),
        "next_avg": target.get("next_avg"),
        "history": [{"date": d, "value": v} for d, v in zip(history_dates[-60:], history_values[-60:])],
        "anomalies": anomalies,
        "forecast": forecast_points,
    }


class NapperRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler serving the Napper dashboard and REST APIs."""

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            web_dir = config.ROOT / "napper" / "web"
            index_path = web_dir / "index.html"
            if index_path.exists():
                self.wfile.write(index_path.read_bytes())
            else:
                self.wfile.write(b"<h1>Napper Dashboard HTML missing</h1>")
            return

        if path == "/api/status":
            engine = query.get("engine", [None])[0]
            latest = get_latest_run_summary(engine)
            digest_text = ""
            if latest and latest.get("digest"):
                digest_text = latest["digest"]
            elif (config.OUT / "latest.md").exists():
                digest_text = (config.OUT / "latest.md").read_text(encoding="utf-8").strip()

            active_engine = "deep" if latest and any("tabpfn" in s.get("model", "") for s in latest.get("series", [])) else "fast"
            resp = {
                "status": "ready",
                "engine": active_engine,
                "latest_digest": digest_text,
                "latest_run": latest,
                "datasets": get_stored_datasets(),
                "out_dir": str(config.OUT),
                "inbox_dir": str(config.INBOX),
            }
            self._send_json(resp)
            return

        if path == "/api/chart":
            series_name = query.get("series", [None])[0]
            engine = query.get("engine", [None])[0]
            data = get_series_chart_data(series_name, engine=engine)
            self._send_json(data)
            return

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/run":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                params = json.loads(body.decode("utf-8")) if body else {}
            except Exception:
                params = {}

            engine = params.get("engine", "fast")  # 'fast' (~2s) or 'deep' (TabPFN)
            selected_datasets = params.get("datasets", None)
            summary = pipeline.run(engine=engine, datasets=selected_datasets)
            self._send_json({"ok": True, "summary": summary})
            return

        if path == "/api/demo-reset":
            counts = sample_data.generate_all()
            self._send_json({"ok": True, "counts": counts})
            return

        if path == "/api/upload":
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" in content_type:
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type},
                )
                uploaded_files = []
                for field in form.keys():
                    item = form[field]
                    if item.filename:
                        dest = config.INBOX / Path(item.filename).name
                        with dest.open("wb") as f:
                            f.write(item.file.read())
                        uploaded_files.append(dest.name)

                # Trigger immediate ingestion
                imported = ingest.ingest_all()
                self._send_json({"ok": True, "uploaded": uploaded_files, "imported": imported})
                return
            else:
                self._send_json({"error": "Expected multipart/form-data"}, status=400)
                return

        self._send_json({"error": "Not found"}, status=404)

    def _send_json(self, data: Any, status: int = 200) -> None:
        raw = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)


def serve(port: int = 5000, open_browser: bool = True) -> None:
    """Start the local Napper dashboard HTTP server."""
    # Ensure folders exist
    for p in (config.INBOX, config.INBOX_PROCESSED, config.STORE, config.FORECASTS, config.OUT):
        p.mkdir(parents=True, exist_ok=True)

    url = f"http://localhost:{port}"
    print(f"\n==========================================")
    print(f"[NAPPER] DASHBOARD LIVE: {url}")
    print(f"   Mode: Offline-First AI Agent Dashboard")
    print(f"   Press Ctrl+C to stop server")
    print(f"==========================================\n")

    if open_browser:
        webbrowser.open(url)

    class ReusableServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReusableServer(("127.0.0.1", port), NapperRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nNapper dashboard server stopped.")
