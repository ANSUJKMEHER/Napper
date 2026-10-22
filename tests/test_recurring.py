import pandas as pd

from napper.recurring import detect_recurring


def test_price_hike_flagged():
    rows = []
    for m in range(1, 7):
        rows.append(
            {
                "date": f"2026-{m:02d}-05",
                "description": "Fitness First Gym",
                "amount": -24.99 if m <= 4 else -29.99,
            }
        )
    df = pd.DataFrame(rows)
    table, events = detect_recurring(df, "date", "description", "amount", min_months=3)
    assert len(table) == 1
    assert table[0]["merchant"] == "fitness first gym"
    hikes = [e for e in events if e["type"] == "price_change"]
    assert len(hikes) == 1
    assert hikes[0]["change_pct"] > 15


def test_one_off_charge_not_recurring():
    rows = []
    for m in range(1, 4):
        rows.append({"date": f"2026-{m:02d}-05", "description": "Fitness First Gym", "amount": -24.99})
    df = pd.DataFrame(rows)
    table, events = detect_recurring(df, "date", "description", "amount", min_months=3)
    assert len(table) == 1  # exactly 3 months still counts
    table2, events2 = detect_recurring(df, "date", "description", "amount", min_months=4)
    assert table2 == []
    assert events2 == []


def test_variable_merchant_never_raises_price_change():
    rows = []
    for m in range(1, 7):
        for _ in range(4):  # groceries: several rows a month, amounts vary a lot
            rows.append({"date": f"2026-{m:02d}-0{_ + 2}", "description": "Greenbasket Grocery", "amount": -round(70 + 20 * ((m * 7 + _) % 5 - 2), 2)})
    df = pd.DataFrame(rows)
    table, events = detect_recurring(df, "date", "description", "amount", min_months=3)
    assert any(r["merchant"] == "greenbasket grocery" and not r["stable"] for r in table)
    assert events == []
