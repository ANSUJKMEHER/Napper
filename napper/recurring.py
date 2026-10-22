"""Recurring-charge detection for bank-like exports.

Finds rows where the same normalized description appears with a stable amount
across >= min_months distinct months, and flags recent amount changes
(price hikes, price drops, one-off extras).

Only "stable" merchants (low month-to-month variation, like subscriptions)
produce price-change events. Merchants whose bill varies a lot month to
month (power, groceries) are listed but never trigger change alerts, so the
digest does not fill up with noise.
"""

from __future__ import annotations

import re

import pandas as pd

from . import config


def normalize_description(desc: str) -> str:
    s = str(desc).lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def detect_duplicate_charges(
    df: pd.DataFrame, date_col: str, description_col: str, amount_col: str
) -> list[dict]:
    """Flag same (day, merchant, amount) debits that appear more than once.

    Catches double charges without any model: two identical rows on the same
    day from the same merchant is a strong signal.
    """
    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    d["merchant"] = d[description_col].astype(str).map(normalize_description).str.strip()
    d["amount"] = pd.to_numeric(d[amount_col], errors="coerce")
    debits = d[d["amount"] < 0].copy()
    debits["amount"] = debits["amount"].abs().round(2)
    dup = debits.groupby([date_col, "merchant", "amount"]).size()
    dup = dup[dup >= 2]
    events: list[dict] = []
    for (dt, merchant, amount), n in dup.items():
        day = pd.Timestamp(dt).strftime("%Y-%m-%d")
        events.append(
            {
                "type": "duplicate_charge",
                "date": day,
                "merchant": merchant,
                "amount": float(amount),
                "count": int(n),
                "message": f"possible duplicate charge: {merchant} billed {n}x ${amount:.2f} on {day}",
            }
        )
    return events


def detect_recurring(
    df: pd.DataFrame,
    date_col: str,
    description_col: str,
    amount_col: str,
    min_months: int = 3,
    change_threshold_pct: float = 10.0,
):
    """Return (table, events).

    table: one row per recurring merchant with typical amount and history.
    events: list of dicts; type "price_change" carries a human message.
    """
    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col])
    d["month"] = d[date_col].dt.to_period("M")
    d["merchant"] = d[description_col].astype(str).map(normalize_description).str.strip()
    d = d[d["merchant"] != ""]
    d["amount"] = pd.to_numeric(d[amount_col], errors="coerce")
    d = d.dropna(subset=["amount"])

    debits = d[d["amount"] < 0].copy()
    debits["amount"] = debits["amount"].abs()

    n_months = debits.groupby("merchant")["month"].nunique()
    merchants = [m for m, n in n_months.items() if n >= min_months]
    if not merchants:
        return [], []

    rec = debits[debits["merchant"].isin(merchants)]
    monthly = rec.groupby(["merchant", "month"])["amount"].agg(["mean", "count"]).reset_index()
    typical = monthly.groupby("merchant")["mean"].median()
    grp = monthly.groupby("merchant")["mean"]
    cv = (grp.std() / grp.mean()).fillna(0.0)  # month-to-month variation

    last_month = monthly["month"].max()

    table: list[dict] = []
    events: list[dict] = []
    for merchant in merchants:
        base = float(typical[merchant])
        lm = monthly[(monthly["merchant"] == merchant) & (monthly["month"] == last_month)]["mean"]
        recent = float(lm.iloc[0]) if len(lm) else None
        stable = float(cv[merchant]) <= 0.10
        table.append(
            {
                "merchant": merchant,
                "typical_amount": round(base, 2),
                "months_seen": int(n_months[merchant]),
                "last_month_amount": round(recent, 2) if recent is not None else None,
                "stable": stable,
                "cv_pct": round(float(cv[merchant]) * 100, 1),
            }
        )
        if stable and recent is not None and base > 0 and abs(recent - base) / base * 100 >= change_threshold_pct:
            sign = "+" if recent > base else "-"
            events.append(
                {
                    "type": "price_change",
                    "merchant": merchant,
                    "typical_amount": round(base, 2),
                    "latest_amount": round(recent, 2),
                    "change_pct": round((recent - base) / base * 100, 1),
                    "message": (
                        f"price change: {merchant} was ${base:.2f}/mo, "
                        f"now ${recent:.2f}/mo ({sign}{(abs(recent - base) / base * 100):.0f}%)"
                    ),
                }
            )
    return table, events
