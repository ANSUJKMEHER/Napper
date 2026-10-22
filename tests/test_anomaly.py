from napper.anomaly import flag_points


def test_spike_flagged_once():
    dates = [f"2026-01-{i:02d}" for i in range(1, 15)]
    expected = [100.0] * 14
    actual = [100.0] * 14
    actual[10] = 1000.0
    flags = flag_points(dates, actual, expected)
    assert len(flags) == 1
    assert flags[0]["date"] == "2026-01-11"
    assert flags[0]["off_pct"] > 500


def test_quiet_series_no_flags():
    dates = [f"2026-01-{i:02d}" for i in range(1, 15)]
    expected = [50.0 + 0.5 * i for i in range(14)]
    actual = [e + 0.2 for e in expected]
    flags = flag_points(dates, actual, expected)
    assert flags == []
