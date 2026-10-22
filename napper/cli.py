"""Napper CLI. python -m napper.cli <command>"""

from __future__ import annotations

import argparse
import sys
import time

from . import config, pipeline


def cmd_init(args):
    for p in (config.INBOX, config.INBOX_PROCESSED, config.STORE, config.FORECASTS, config.OUT, config.LOG_DIR):
        p.mkdir(parents=True, exist_ok=True)
    print("Napper folders ready.")
    print(f"Drop CSVs into {config.INBOX}, then run: python -m napper.cli run")


def cmd_run(args):
    summary = pipeline.run()
    print("\n=== NAPPER RUN ===")
    if summary["imported"]:
        for row in summary["imported"]:
            print(f"imported {row['dataset']} ({row['rows']} rows)")
    for s in summary["series"]:
        if "error" in s:
            print(f"! {s['name']}: {s['error']}")
            continue
        print(
            f"* {s['name']}: model={s.get('model')} next={s.get('next_sum')} "
            f"wmape={s.get('wmape_pct')}% anomalies={len(s.get('history_anomalies', []))}"
        )
    for ev in summary["events"]:
        print(f"! event: {ev.get('message', ev)}")
    print("\n--- digest ---")
    print(summary["digest"])
    print(f"\n(digest writer: {summary['digest_writer']}; {summary['elapsed_seconds']}s)")


def cmd_demo(args):
    from .sample_data import generate_all

    counts = generate_all()
    print("Generated sample CSVs in inbox/: " + ", ".join(f"{k}={v} rows" for k, v in counts.items()))
    cmd_run(args)


def cmd_watch(args):
    print(f"Watching inbox every {args.minutes} min. Ctrl+C to stop.")
    try:
        while True:
            cmd_run(args)
            time.sleep(args.minutes * 60)
    except KeyboardInterrupt:
        print("\nNapper went back to sleep.")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="napper", description="The agent that works while you sleep.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create the folder layout").set_defaults(func=cmd_init)
    sub.add_parser("run", help="one full overnight run (ingest + forecast + digest)").set_defaults(func=cmd_run)
    sub.add_parser("demo", help="generate sample data and run").set_defaults(func=cmd_demo)
    w = sub.add_parser("watch", help="loop run() every N minutes")
    w.set_defaults(func=cmd_watch)
    w.add_argument("--minutes", type=int, default=60)
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
