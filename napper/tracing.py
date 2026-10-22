"""Sentry Agent Tracing instrumentation for Napper.

Provides distributed tracing, spans, and observability for the overnight agent
workflow, including tabular foundation model inference, anomaly detection tools,
and local LLM digest generation. Cost is tracked as $0.00 for open local runs.
"""

from __future__ import annotations

import contextlib
import os
import time
from typing import Any, Iterator

try:
    import sentry_sdk
    from sentry_sdk.tracing import Span
    HAS_SENTRY = True
except ImportError:
    HAS_SENTRY = False
    Span = Any  # type: ignore

from . import config


def init_tracing() -> bool:
    """Initialize Sentry SDK with AI Agent Tracing options if DSN is set."""
    if not HAS_SENTRY:
        return False

    dsn = config.SENTRY_DSN or os.getenv("SENTRY_DSN")
    if not dsn:
        return False

    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        send_default_pii=True,
        release="napper@0.1.0",
        environment=os.getenv("NAPPER_ENV", "production"),
    )

    sentry_sdk.set_tag("agent.name", "napper")
    sentry_sdk.set_tag("agent.type", "offline-predictive-sloth")
    sentry_sdk.set_tag("challenge", "hacktoberfest-2026-week3")
    sentry_sdk.set_context(
        "agent",
        {
            "name": "Napper",
            "runtime": "local-offline",
            "forecaster": "TabPFN-3.5",
            "digest_model": config.DIGEST_MODEL,
            "cost_per_run_usd": 0.0,
        },
    )
    return True


@contextlib.contextmanager
def trace_step(
    op: str,
    description: str,
    data: dict[str, Any] | None = None,
    tags: dict[str, str] | None = None,
) -> Iterator[Any]:
    """Context manager for tracing an agent step or tool execution.
    
    Gracefully degrades to a no-op if Sentry is not configured.
    """
    if not HAS_SENTRY or not sentry_sdk.is_initialized():
        yield None
        return

    with sentry_sdk.start_span(op=op, description=description) as span:
        if tags:
            for k, v in tags.items():
                span.set_tag(k, v)
        if data:
            for k, v in data.items():
                span.set_data(k, v)
        # Record zero compute cost for local open models
        span.set_data("ai.cost", 0.0)
        span.set_data("gen_ai.usage.cost", 0.0)
        try:
            yield span
        except Exception as exc:
            span.set_status("internal_error")
            sentry_sdk.capture_exception(exc)
            raise


def record_cost_metric(amount_usd: float = 0.0) -> None:
    """Record run cost measurement (always $0.00 for Napper local stack)."""
    if HAS_SENTRY and sentry_sdk.is_initialized():
        sentry_sdk.set_measurement("ai_cost_usd", amount_usd, unit="usd")
