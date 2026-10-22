# Napper

The agent that works while you sleep. Drop a CSV into a folder and go to bed.
In the morning there is a two-line digest telling you what is coming and what
is weird. Forecasts come from TabPFN-3.5 (open-weight, local, $0). The digest
is written by a local Gemma model. Your data never leaves the machine, and the
whole thing runs in airplane mode.

Built for the Hacktoberfest 2026 DEV Challenge Week 3: Slow and Steady
(`#hf26challenge`, `#devchallenge`).

## Why it exists

I am lazy in the specific way that makes you automate things. I was tired of
opening three apps every morning to check my bank, my power bill, and my step
count. So Napper watches the CSVs those apps export, and I watch nothing.

The sloth part: Napper does not answer questions. It runs overnight on a
schedule, spends as much time as it wants, and hands me two lines before my
alarm. Slow and steady.

The open part: TabPFN-3.5 and Gemma are open-weight. Both run locally. My bank
statement never goes to a server I do not control, nothing has a usage bill,
and I can swap either model for a different one tomorrow. A closed hosted
forecast API cannot offer any of that.

## Quickstart

```bash
pip install -r requirements.txt
python -m napper.cli demo        # generate 3 sample CSVs and run the whole pipeline
cat out/latest.md                # the morning digest
```

Drop your own CSV (any file with a date column and numbers) into `inbox/` and
run `python -m napper.cli run`. Re-dropping a file is safe: imports are
deduped by content hash.

Real engines (optional but recommended):

```bash
pip install tabpfn              # TabPFN-3.5; accept the license at platform.priorlabs.ai on first fit
ollama pull gemma3              # then keep Ollama running for the LLM digest
```

Without them the pipeline still works, using a linear-detrended naive baseline
and a template digest.

## What it catches

The demo data plants three storylines on purpose, and the demo run catches all
three:

1. a gym price hike (24.99 -> 29.99), found by the recurring-charge detector
2. a forgotten monthly subscription (Streamly, 13 months), listed in the
   recurring table
3. a double electricity charge and a 3-day kWh spike, found by the
duplicate-charge detector and the walk-forward screen (which flags exactly
the three spike days and nothing else)

Run `python -m napper.cli demo` and read `out/latest.md` to see it yourself.

## How it works

```
inbox/*.csv  ->  ingest (normalize, dedupe by hash)  ->  data/store/{dataset}.csv
store        ->  series: monthly spend (bank-like) or daily numeric columns (kwh, steps)
series       ->  TabPFN-3.5 with calendar + lag features, recursive horizon (naive fallback)
store        ->  recurring-charge detection (stable vs variable merchants, price-change alerts)
store        ->  duplicate-charge detection (same day, merchant, amount)
series       ->  walk-forward anomaly screen (median of prior same weekdays, robust band)
results      ->  Gemma digest via Ollama (template fallback)  ->  out/digest.md
```

A tabular foundation model sees a time series as rows of calendar and lag
features; the horizon is produced by recursive one-step prediction. Spend is
forecast monthly (weekly totals are bimodal: rent week versus no-rent week),
and a daily diagnostic series is added automatically when TabPFN is installed,
because a tabular model can learn day-of-month patterns that the naive
baseline cannot. The naive baseline is always computed alongside every
forecast, so each run carries its own comparison point. See
`experiments/tortoise_vs_hare.py` for the closed-vs-open table used in the
write-up.

## Repository layout

- `napper/` — the package (ingest, recurring, forecast, anomaly, digest, pipeline, cli)
- `scripts/make_sample_data.py` — deterministic demo CSVs with planted events
- `experiments/tortoise_vs_hare.py` — closed-vs-open comparison table
- `scheduler/temporal_workflow.py` — optional v2: durable Temporal workflow (v1 is cron)
- `tests/` — pytest suite for ingest, recurring, and anomaly logic
- `data/`, `out/` — kept in the repo on purpose: sample data, forecasts, and
  digest history are part of the evidence

## Scheduling

v1: `0 3 * * * cd /path/to/napper && python -m napper.cli run`
v2: the Temporal workflow in `scheduler/temporal_workflow.py` makes the run
durable and resumable.

## License notes

Code in this repository: your choice (suggest MIT).
TabPFN-3.5 model weights are released under a non-commercial license by Prior
Labs; accept it at platform.priorlabs.ai before first use. Gemma is Google's
open-weight model, used here via Ollama.

## Team

[fill in DEV handles, max 4]

_Repo created inside the Hacktoberfest Week 3 challenge window (Oct 19-25, 2026)._
_Any commits after the submission deadline will be listed here._
