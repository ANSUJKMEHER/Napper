"""Paths and settings for Napper."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent

INBOX = ROOT / "inbox"
INBOX_PROCESSED = ROOT / "inbox" / "processed"
DATA = ROOT / "data"
STORE = DATA / "store"
FORECASTS = DATA / "forecasts"
OUT = ROOT / "out"
LOG_DIR = ROOT / "logs"

# Observability and API settings
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
TABPFN_TOKEN = os.getenv("TABPFN_TOKEN", "")

# Ollama settings for the local Gemma digest.
DIGEST_MODEL = os.getenv("DIGEST_MODEL", "gemma3:12b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

FORECAST_HORIZON_DAYS = 30
HOLDOUT_DAYS = 14
ANOMALY_SIGMA = 2.5
ANOMALY_MIN_PCT = 15.0  # only flag points off by at least this many percent
WALK_FORWARD_MIN_PCT = 40.0  # tighter bar for the same-season screen
WALK_FORWARD_WINDOW_DAYS = 60

DATE_COLUMN_NAMES = ("date", "day", "ds", "timestamp", "datetime")

