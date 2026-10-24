from unittest.mock import MagicMock, patch

from napper import digest


def test_template_digest_formatting():
    context = {
        "date": "2026-10-24",
        "forecasts": [
            {
                "name": "bank:spend",
                "model": "tabpfn-3.5",
                "next_sum": 1904.17,
                "wmape_pct": 2.03,
                "history_anomalies": [
                    {"note": "2026-09-16: 57.70 vs expected 15.95 (+262%)"}
                ],
            }
        ],
        "events": [
            {"type": "price_change", "message": "fitness first gym was $24.99/mo, now $29.99/mo (+20%)"},
            {"type": "duplicate_charge", "message": "city power light billed 2x $77.86 on 2026-09-20"},
        ],
    }
    result = digest.template_digest(context)
    lines = result.strip().split("\n")
    assert len(lines) == 2
    assert "1904.17" in lines[0]
    assert "tabpfn-3.5" in lines[0]
    assert "fitness first" in lines[1]
    assert "city power" in lines[1]
    assert "+262%" in lines[1]


def test_build_gemma_prompt():
    context = {
        "date": "2026-10-24",
        "forecasts": [
            {
                "name": "bank:spend",
                "model": "tabpfn-3.5",
                "next_sum": 1904.17,
                "next_avg": 63.47,
                "wmape_pct": 2.03,
                "history_anomalies": [{"note": "kwh spike (+262%)"}],
            }
        ],
        "events": [{"message": "duplicate charge 2x $77.86"}],
    }
    prompt = digest.build_prompt(context)
    assert "Today is 2026-10-24" in prompt
    assert "bank:spend" in prompt
    assert "tabpfn-3.5" in prompt
    assert "duplicate charge" in prompt
    assert "kwh spike" in prompt


@patch("requests.post")
def test_gemma_digest_mock(mock_post):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "response": (
            "Next month bank spend is forecast at $1,904.\n"
            "Notice: Gym fee rose to $29.99, power bill charged twice, and a 3-day power spike occurred."
        )
    }
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp

    prompt = "Test prompt"
    out = digest.gemma_digest(prompt)
    assert out is not None
    assert "1,904" in out
    assert mock_post.called
