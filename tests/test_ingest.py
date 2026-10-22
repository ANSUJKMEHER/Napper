from pathlib import Path

import pandas as pd

from napper import config, ingest


def _setup(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(config, "INBOX", tmp_path / "inbox")
    monkeypatch.setattr(config, "INBOX_PROCESSED", tmp_path / "inbox" / "processed")
    monkeypatch.setattr(config, "STORE", tmp_path / "store")
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    (tmp_path / "inbox").mkdir(parents=True)


def test_ingest_dedupes_identical_files(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    (config.INBOX / "a.csv").write_text("date,amount\n2026-01-01,10\n2026-01-02,20\n")
    (config.INBOX / "b.csv").write_text("date,amount\n2026-01-01,10\n2026-01-02,20\n")
    imported = ingest.ingest_all()
    assert len(imported) == 1
    assert imported[0]["rows"] == 2


def test_currency_strings_become_numeric(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    (config.INBOX / "money.csv").write_text(
        'date,amount\n2026-01-01,"$1,234.56"\n2026-01-02,"$45.00"\n'
    )
    ingest.ingest_all()
    store = pd.read_csv(config.STORE / "money.csv")
    assert pd.api.types.is_numeric_dtype(store["amount"])
    assert store["amount"].iloc[0] == 1234.56
