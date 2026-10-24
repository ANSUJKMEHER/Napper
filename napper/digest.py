"""Morning digest: two lines, written by local Gemma when Ollama is up.

If Ollama is unreachable, a deterministic template digest takes over, so the
pipeline still produces something useful on a bare machine.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from . import config, tracing

SYSTEM = (
    "You are Napper, a tiny local agent that watches a person's CSVs overnight. "
    "Write a morning brief of exactly two lines, plain language, no greeting, no filler, no headings. "
    "Line 1: the single most useful forecast for the coming month. "
    "Line 2: anything odd worth checking (price changes, anomalies, surprises). "
    "If nothing is odd, say that briefly. Keep it under 45 words total. Round all numbers."
)


def build_prompt(context: dict) -> str:
    lines = [f"Today is {context['date']}. What I know:"]
    for f in context.get("forecasts", []):
        lines.append(
            f"- {f['name']}: model {f['model']}, next period sum ~{f['next_sum']} "
            f"(avg {f['next_avg']}), holdout error {f.get('wmape_pct')}%"
        )
    for ev in context.get("events", []):
        lines.append(f"- event: {ev.get('message', ev)}")
    for f in context.get("forecasts", []):
        for a in f.get("history_anomalies", [])[:5]:
            lines.append(f"- anomaly: {a['note']}")
    return "\n".join(lines)


def gemma_digest(prompt: str, model: str | None = None, url: str | None = None) -> str | None:
    """Ask local Ollama for the two lines. Returns None if unavailable."""
    try:
        import requests
    except ImportError:
        return None
    try:
        with tracing.trace_step(
            "ai.chat_completions",
            "ollama_gemma_digest",
            data={
                "gen_ai.system": "ollama",
                "gen_ai.request.model": model or config.DIGEST_MODEL,
                "ai.cost": 0.0,
            },
        ):
            r = requests.post(
                url or config.OLLAMA_URL,
                json={
                    "model": model or config.DIGEST_MODEL,
                    "system": SYSTEM,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120,
            )
            r.raise_for_status()
            text = (r.json().get("response") or "").strip()
            return text or None
    except Exception:
        return None


def _ranked_notes(forecasts: list[dict]) -> list[str]:
    """Anomaly notes sorted by severity (biggest percent-off first)."""
    notes = []
    for x in forecasts:
        s_name = x.get("name", "")
        series_label = s_name.split(":")[0] if ":" in s_name else s_name
        for a in x.get("history_anomalies", []):
            raw_note = a.get("note", "")
            if not raw_note.lower().startswith(series_label.lower()):
                notes.append(f"{series_label}: {raw_note}")
            else:
                notes.append(raw_note)
    return sorted(notes, key=lambda n: _severity(n), reverse=True)


def _severity(note: str) -> float:
    # notes end with e.g. "(+200%)"; parse it for ranking, default 0
    import re

    m = re.search(r"\(([+-]?\d+)%\)", note)
    return float(m.group(1)) if m else 0.0


def template_digest(context: dict) -> str:
    """Deterministic fallback: works with zero external services."""
    forecasts = context.get("forecasts", [])
    if not forecasts:
        return "Nothing new in the inbox.\n"
    f = next((x for x in forecasts if x["name"].endswith(":spend")), forecasts[0])
    line1 = (
        f"{f['name'].split(':')[0]} next month: ~{f['next_sum']} "
        f"(local model {f['model']}, holdout error {f.get('wmape_pct')}%)."
    )
    odds = [ev.get("message", str(ev)) for ev in context.get("events", [])]
    odds += _ranked_notes(forecasts)
    line2 = "; ".join(odds[:3]) if odds else "Nothing odd spotted."
    return f"{line1}\n{line2}"


def write_digest(text: str, when: date | None = None) -> Path:
    when = when or date.today()
    config.OUT.mkdir(parents=True, exist_ok=True)
    header = f"## {when.isoformat()}"
    history = config.OUT / "digest.md"
    with history.open("a", encoding="utf-8") as f:
        f.write(f"{header}\n{text}\n\n")
    (config.OUT / "latest.md").write_text(f"{header}\n{text}\n", encoding="utf-8")
    return history
