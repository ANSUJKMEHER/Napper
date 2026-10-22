"""Optional v2 scheduler: durable Temporal workflow for the overnight run.

v1 (zero dependencies) is a plain cron line:
    0 3 * * *  cd /path/to/napper && python -m napper.cli run

This file upgrades the run into a durable Temporal workflow so it survives
crashes, retries flaky steps, and picks up where it left off. That is the
"slow and steady" part made explicit: the work is allowed to take all night,
and it cannot be lost.

Setup: pip install temporalio && temporal server start-dev
Then register a schedule so the workflow fires at 03:00 local time.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from temporalio import activity, workflow  # noqa: E402
from temporalio.common import RetryPolicy  # noqa: E402

from napper import pipeline  # noqa: E402


@activity.defn
async def overnight_run_activity() -> dict:
    """One full Napper run as a resumable unit (ingest + forecast + digest)."""
    return pipeline.run()


@workflow.defn
class OvernightRun:
    @workflow.run
    async def run(self) -> str:
        summary = await workflow.execute_activity(
            overnight_run_activity,
            start_to_close_timeout=timedelta(hours=2),
            retry_policy=RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=30)),
        )
        return str(summary.get("digest") or "no digest")


if __name__ == "__main__":
    print(
        "This is a workflow definition, not an entrypoint. "
        "Run a Temporal worker and a schedule; see docs at https://docs.temporal.io"
    )
