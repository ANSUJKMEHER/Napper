"""CSV drop-zone ingestion.

Every new CSV in inbox/ is normalized into data/store/{dataset}.csv.
Idempotent: files are tracked by content hash in data/manifest.json, so
re-dropping a file (even under another name) never double-imports.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import config


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "dataset"


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_csv(path: Path) -> pd.DataFrame:
    """Try common delimiters and encodings; raise the last error if all fail."""
    last_err: Exception | None = None
    for sep in (",", ";", "\t", "|"):
        try:
            return pd.read_csv(path, sep=sep, encoding="utf-8-sig")
        except Exception as exc:  # noqa: BLE001 - we try the next delimiter
            last_err = exc
    assert last_err is not None
    raise last_err


def _coerce_numeric(series: pd.Series) -> pd.Series:
    """Turn obviously-numeric string columns into numbers; leave text alone."""
    if pd.api.types.is_numeric_dtype(series):
        return series
    s = series.astype(str).str.strip()
    s = s.str.replace(r"^[$\u20ac\u00a3]\s*", "", regex=True)
    s = s.str.replace(",", "", regex=False)  # drop thousands separators
    out = pd.to_numeric(s, errors="coerce")
    if out.notna().mean() >= 0.9:
        return out
    return series


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase/snake_case columns, parse the date column, coerce numerics."""
    df = df.copy()
    df.columns = [re.sub(r"\s+", "_", str(c).strip().lower()) for c in df.columns]
    df = df.dropna(how="all")

    date_col = None
    for c in df.columns:
        if c in config.DATE_COLUMN_NAMES:
            date_col = c
            break
    if date_col is None:
        for c in df.columns:
            try:
                df[c] = pd.to_datetime(df[c], errors="raise")
                date_col = c
                break
            except (ValueError, TypeError):
                continue
    if date_col is not None:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col])

    for c in df.columns:
        if c == date_col:
            continue
        df[c] = _coerce_numeric(df[c])
    return df


def _load_manifest() -> dict:
    p = config.DATA / "manifest.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}


def _save_manifest(manifest: dict) -> None:
    config.DATA.mkdir(parents=True, exist_ok=True)
    (config.DATA / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))


def ingest_all() -> list[dict]:
    """Import every new CSV from the inbox. Returns one dict per import."""
    config.INBOX.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest()
    imported: list[dict] = []
    for path in sorted(config.INBOX.glob("*.csv")):
        digest = _file_hash(path)
        if digest in manifest:
            continue
        df = normalize(_read_csv(path))
        if df.empty:
            continue
        dataset = slugify(path.stem)
        store = config.STORE / f"{dataset}.csv"
        config.STORE.mkdir(parents=True, exist_ok=True)
        if store.exists():
            df.to_csv(store, mode="a", header=False, index=False)
        else:
            df.to_csv(store, index=False)
        rows = len(df)
        manifest[digest] = {
            "dataset": dataset,
            "rows": rows,
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "source": path.name,
        }
        _save_manifest(manifest)
        archived = config.INBOX_PROCESSED / path.name
        config.INBOX_PROCESSED.mkdir(parents=True, exist_ok=True)
        if archived.exists():
            archived = config.INBOX_PROCESSED / f"{path.stem}-{digest[:8]}.csv"
        path.rename(archived)
        imported.append({"dataset": dataset, "rows": rows, "archived_as": archived.name})
    return imported
