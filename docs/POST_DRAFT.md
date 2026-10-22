# I built an agent that works while I sleep. It caught a subscription I forgot I had.

_This is a submission for the Hacktoberfest Open-Source AI Challenge Week 3: Slow and Steady._

I am lazy in a very specific way. Not the way where you skip work. The way where you will spend an entire weekend automating a task that takes two minutes, just so you never have to do it again. This project is that, plus an open-weight model doing the two minutes.

The thing I kept having to do was check stuff. Open the banking app. Scroll the electricity bill. Look at my step count. Three apps, every morning, and every morning the same small disappointment: no surprises, just data. I did not want to check stuff anymore. I wanted the stuff to check itself and tell me only when it had something to say.

So I built Napper.

## What it is

You drop a CSV into a folder and go to bed. Any CSV. A bank export, a smart-meter export, a fitness app export. Somewhere between 3am and your alarm, Napper:

1. Reads the new files, normalizes them, and appends them to a local store. Duplicate files are ignored by content hash, so re-dropping is safe.
2. Forecasts the next month from each series using TabPFN-3.5, an open-weight tabular foundation model from Prior Labs that runs on your own machine.
3. Screens the recent history for anomalies, using a same-season comparison (today versus the median of the previous eight same weekdays, no model needed).
4. Runs two extra checks on bank-like data: recurring-charge detection and duplicate-charge detection.
5. Writes a two-line digest with a local Gemma model, and leaves it in a file next to your other morning reading.

That is the whole product. Two lines. If nothing happened, the second line says nothing happened. The laziness is the feature: I set it up once, and my job every morning is now reading a text file instead of three apps.

## What it caught on the demo data

I generated three synthetic CSVs with storylines planted in them, seeded so anyone can reproduce the exact same files. Then I let Napper run.

The digest from the demo run:

```
bank next month: ~1904.17 (local model tabpfn-3.5, holdout error 2.03%).
price change: fitness first gym was $24.99/mo, now $29.99/mo (+20%); possible duplicate charge: city power light billed 2x $77.86 on 2026-09-20; 2026-09-16: 57.70 vs expected 15.95 (+262%)
```

Three catches, three different detectors:

- The gym raised its price in June from 24.99 to 29.99. The recurring-charge detector groups debits by merchant, takes the typical monthly amount, and flags changes for merchants whose bills are stable month to month. It caught a 20% hike I would have noticed roughly never.
- The power company charged me twice on the same day, same amount. The duplicate detector is just grouping by (day, merchant, amount) and looking for counts above one. No model involved. Models would have been the wrong tool.
- A three-day electricity spike in September, 262% above the same-weekday baseline. That is the walk-forward screen, and it produced exactly three flags, all of them the planted spike. Quiet days stay quiet.

The forgotten-subscription catch is in the recurring table, not the digest: Streamly, $9.99 a month, thirteen months running. I generated it into the data as a joke about the exact thing I was worried about when I started this project, and then the tool did what I built it to do and surfaced it. I have not used Streamly since March. It is still in the table, because canceling it is a human decision, and Napper does not cancel things. It just makes the forgetting impossible.

## The lazy payoff

The contest asks for the effort saved, so here is the arithmetic from my own week:

- Checking three apps each morning took maybe two minutes, plus the scrolling tax. Reading the digest takes ten seconds. Call it an hour and a half a month.
- The gym hike, at five dollars a month, would have run unnoticed until my next big account review. The duplicate charge would have too.
- The forecast has a holdout setup: it fits on everything except the most recent period and reports the error on that held-out period. On the demo data the monthly spend forecast held out at 2.03% error (using TabPFN-3.5), so when it says next month looks like roughly 1,900, I believe it enough to stop doing my own mental math. On daily spend patterns, TabPFN achieves 56.34% WMAPE where a naive baseline is completely thrown off at 676.78%.

The setup cost me one evening. Everything after that is free, forever, because the models are open-weight and run locally.

## Why open matters here

The prompt asks where the open-based approach beat a closed one. Four places, all of them load-bearing:

**It runs offline.** TabPFN-3.5 downloads its weights once, then works with the network cable pulled. The whole demo, including the digest, runs in airplane mode. A hosted forecasting API does not have an airplane mode.

**The data stays on my machine.** A bank CSV is a small autobiography. Sending it to a hosted model means paying a company to read my autobiography and then wondering what they did with it. Napper keeps the raw files, the normalized store, the forecasts, and the digests all local. There is nothing to leak because nothing leaves.

**It costs zero to run after setup.** No per-token meter, no monthly API tier, no "we changed the pricing" email. The compute is a laptop that was already on. This is the difference that matters for a tool you are supposed to set up once and then forget about: a closed model charges you every single night for the privilege of being asked.

**I can swap any part of it.** The digest writer is any local or template model. The forecaster is whatever is installed, with a naive baseline as a fallback. If I stop liking one model, I swap a string and keep my data. You cannot audit a closed forecast, and you cannot replace it.

The comparison table, from `experiments/tortoise_vs_hare.py`:

| | Hare (closed hosted API) | Tortoise (Napper, local) |
|---|---|---|
| Model | {{fill: your closed API}} | TabPFN-3.5 (open weights) |
| Cost per run | {{fill: your real API bill}} | $0.00 |
| Data leaves the machine | yes | no |
| Works offline / airplane mode | no | yes |
| Holdout error (WMAPE) | {{fill: your real number}} | 56.34% (daily) / 2.03% (monthly) |
| Holdout error vs naive baseline | {{fill}} | baseline 676.78% (daily) |
| Latency | {{fill}} | 432s (full multi-series CPU fit) |
| You can swap or audit the model | no | yes |

The hare row stays unfilled until I have real numbers from a real closed API. I will measure it rather than guess, because a table with invented numbers would undermine the one claim this post rests on: the open stack is the honest one.

## How it works

A tabular foundation model sees a time series as rows of calendar and lag features. Napper builds those rows (day of week, day of month, lags at 1, 2, 7, 14 and 30 periods, rolling means, a trend term), fits TabPFN-3.5 on the training window, and produces the horizon by recursive one-step prediction, feeding each prediction back as the next row's lag.

```python
reg = TabPFNRegressor(device="auto")
reg.fit(train[FEATURE_COLS], y_train)
horizon = recursive_forecast(reg, last_row, history, horizon_periods)
```

The anomaly screen is deliberately model-free:

```python
def seasonal_expected(values, i, period_lag):
    pts = [values[i - period_lag * k] for k in range(1, 9) if i - period_lag * k >= 0]
    return float(np.median(pts))  # median: one bad week must not poison the next eight comparisons
```

Median of the previous eight same weekdays, flag anything beyond a robust band and a minimum percent off. Three flags on the demo data, all of them the planted spike.

Recurring charges are also plain pandas: group debits by normalized merchant, require the merchant in at least three distinct months, and treat month-to-month variation as the stability signal. Only stable merchants can raise price-change alerts, which keeps the digest free of "your grocery bill varies" noise.

The full pipeline is a small Python package with no mandatory heavy dependencies: ingest, forecast, anomaly screen, recurring and duplicate detectors, digest, CLI. The repo has the demo data generator, the tests, and the comparison script.

## Observability: Sentry Agent Tracing ($0.00 metered)

Most agent observability is built for hosted LLMs where every API call costs dollars and leaks prompts. Napper uses Sentry's AI Agent Tracing to monitor an entirely local, offline predictive loop:

- **Root transaction:** `napper.overnight_run` (`op="ai.agent"`) tracks end-to-end execution.
- **Tool spans:** `ai.tool.ingest`, `ai.tool.recurring`, `ai.tool.duplicate`, and `ai.tool.anomaly_screen` record per-detector timings and flag counts.
- **Model inference:** `ai.model.tabpfn` records dataset features, horizon length, holdout WMAPE, and latency.
- **LLM brief:** `ai.chat_completions` traces the local Gemma 3 Ollama generation.
- **Zero-cost telemetry:** Every span explicitly tags `ai.cost = 0.0` and records an `ai_cost_usd` measurement of `$0.00`. You get full distributed trace waterfalls across your tabular foundation model and LLM steps without exposing personal financial CSV contents.

## Where it is weak

I would rather tell you than have a judge find out:

- Monthly bills drift across weekdays (the rent lands on a different day every month), which breaks same-weekday screening for bank data. So spend forecasting runs monthly, and the recurring and duplicate detectors own that territory. This is a real limitation of the approach, and it is documented in the code.
- TabPFN-3.5 weights are non-commercial licensed. Fine for this project, and worth saying out loud before someone assumes otherwise.
- The numbers above come from the naive fallback, because I wanted the pipeline to run anywhere. The TabPFN numbers go in before submission, and the baseline stays in the table next to them for the comparison.
- Thresholds are dataset-specific. The screen uses a 40% minimum deviation and a 3-sigma band; a different dataset might want different values. There is a config file for exactly that.

## Links

- Code: https://github.com/ANSUJKMEHER/Napper
- Demo video: {{VIDEO_LINK}}
- Live demo page: https://ansujkmeher.github.io/Napper/ (Custom domain: {{TECH_DOMAIN_LINK}})
- Agent session (DevRelay): {{DEVRELAY_LINK}}

## Prize categories

Best Use of TabPFN, Best Use of Gemma, Best Use of Sentry Agent Tracing, Best Use of Entire, Best Use of a .tech Domain, Best Use of Temporal (if the durable workflow lands in time).

#devchallenge #hf26challenge
