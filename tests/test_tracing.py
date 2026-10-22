import pytest
from napper import tracing


def test_tracing_unconfigured():
    """When SENTRY_DSN is not configured, tracing degrades to a clean no-op."""
    assert tracing.init_tracing() is False
    executed = False
    with tracing.trace_step("ai.tool.test", "test span"):
        executed = True
    assert executed is True
    # Should not raise
    tracing.record_cost_metric(0.0)


def test_tracing_exception_propagation():
    """Exceptions within a traced span must bubble up cleanly."""
    with pytest.raises(ValueError, match="intentional"):
        with tracing.trace_step("ai.test", "failing step"):
            raise ValueError("intentional")
