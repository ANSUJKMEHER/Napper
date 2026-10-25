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
5. Writes a concise morning brief — typically two lines per source, and on quiet mornings, almost nothing — and leaves it in a file next to your other morning reading.

That is the whole product. A concise brief that scales strictly to genuine signals: a clean forecast headline, plus only verified alerts. If nothing happened, it says nothing happened. The laziness is the feature: I set it up once, and my job every morning is now reading a 10-second text file instead of three apps.

## What it caught on the demo data

I generated four synthetic CSVs (`bank`, `electricity`, `steps`, and `water`) with storylines planted in them, seeded so anyone can reproduce the exact same files across 1,110 data points. Then I let Napper run.

The digest from the TabPFN run (`out/latest.md`):

```
bank next month: ~1904.17 (local model tabpfn-3.5, holdout error 2.03%).
price change: fitness first gym was $24.99/mo, now $29.99/mo (+20%); possible duplicate charge: city power light billed 2x $77.86 on 2026-09-20; water spike: 425.0 liters on 2026-10-19 (expected ~52.8 liters, +706%)
```

Four catches, four different detectors:

- **Gym Price Hike:** The gym raised its price from $24.99 to $29.99 (+20%). The recurring-charge detector groups debits by merchant, takes the typical monthly amount, and flags changes for merchants whose bills are stable month to month. It caught a 20% hike I would have noticed roughly never.
- **Double Billing:** The power company charged me twice on the same day for the exact same amount ($77.86 x2 on 2026-09-20). The duplicate detector groups by (day, merchant, amount) and looks for counts above one. No model involved. A model would have been the wrong tool.
- **3-Day Electricity Spike:** An electricity spike in September, 262% above the same-weekday baseline (57.70 kWh vs 15.95 kWh). That is the walk-forward screen, and it produced zero false alarms across the entire 386-day history.
- **Water Pipe Burst:** A catastrophic spike on October 18–19 where water usage surged to 425.0 liters/day against an expected baseline of 52.8 liters (+706%). In real life, catching a plumbing leak on Day 1 saves hundreds in utility bills and thousands in water damage.

The forgotten-subscription catch is in the recurring audit table: Streamly, $9.99 a month, thirteen months running. I generated it into the data as a joke about the exact thing I was worried about when I started this project, and then the tool did what I built it to do and surfaced it. I have not used Streamly since March. It is still in the table, because canceling it is a human decision, and Napper does not cancel things. It just makes the forgetting impossible.

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

The comparison table, measured against a zero-shot GPT-4o-mini prompt forecast (reproducible code and artifact at `experiments/hare_measure.py` and `data/hare/run.json`):

| Attribute | Hare (Closed Hosted API: GPT-4o-mini) | Tortoise (Napper: TabPFN-3.5 Local) |
|---|---|---|
| **Model Type** | Proprietary Cloud API (`gpt-4o-mini`) | TabPFN-3.5 (Open-Weight Foundation Model) |
| **Cost Per Run** | ~$0.0123 / run (token usage & cloud fees) | **$0.00 (Zero runtime cost)** |
| **Data Privacy** | ❌ Data leaves machine (bank transactions sent over cloud) | **✅ 100% Local (0 bytes transmitted)** |
| **Offline Capable** | ❌ Fails without active internet connection | **✅ Works in airplane mode / air-gapped** |
| **Holdout Error (Daily Spend WMAPE)** | 165.45% (Prompted zero-shot token regression) | **56.34% (3x better than GPT-4o-mini, 12x better than naive)** |
| **Monthly Spend WMAPE** | 4.85% | **2.03%** |
| **Execution Latency** | ~3.42s (Network API round-trip) | ~432s (Local AMD Ryzen CPU "Slow & Steady") |
| **Auditability & Portability** | ❌ Closed black box; subject to vendor deprecation | **✅ Open weights, fully auditable, swappable** |

While the closed hosted API is fast to reply over the wire, it leaks personal financial data and costs recurring money every single night. Furthermore, zero-shot prompted LLMs struggle with day-of-month and weekday arithmetic, yielding 165.45% error. The tortoise takes its time overnight on local consumer silicon ("Slow and Steady"), delivers superior predictive precision (56.34%), and costs literally $0.00.

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

The full pipeline is a small Python package with no mandatory heavy dependencies: ingest, forecast, anomaly screen, recurring and duplicate detectors, digest, CLI, and an interactive local dashboard (`python -m napper.cli web`). The repo has the demo data generator, the test suite, and the comparison script.

## Interactive Local Dashboard & Web Audio Brief

To make exploring your data effortless, Napper provides a local web interface:

```bash
python -m napper.cli web
```

- **Drag-and-Drop Ingestion:** Drop raw bank, power, or step CSVs into the inbox without touching the command line.
- **Dual Speed (Nap vs Deep Sleep):** Instant ~2s mode for quick UI testing or the full TabPFN-3.5 model run for high-precision overnight forecasts.
- **Predictive Foundation Visualizer:** Interactive Chart.js charts showing observed history, 30-day forecast horizons, and isolated anomalies in red.
- **Text-to-Speech:** Click "Listen to Brief" to have your morning summary read aloud via the Web Speech API.
- **Sentry Waterfall:** Visual verification of all pipeline spans and $0.00 metered cost.

A static mirror of the dashboard is hosted live at [https://ansujkmeher.github.io/Napper/](https://ansujkmeher.github.io/Napper/).

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
- The TabPFN-3.5 numbers in the table are measured on our test machine (AMD Ryzen 5 5625U CPU, 16GB RAM) running full multi-series recursive inference. On CPU, it takes ~15 minutes ("Slow and Steady"); on an NVIDIA GPU, it executes in seconds. We provide both Deep Sleep (TabPFN-3.5) and Nap Mode (~2s) so anyone can test it easily.
- **Gemma Local Execution:** The recorded demo runs the deterministic template digest because my test laptop (integrated AMD graphics) cannot comfortably host a heavy 9GB Ollama LLM. The Gemma bridge is implemented in `napper/digest.py`, fully unit-tested, and activates automatically wherever Ollama is running.
- Thresholds are dataset-specific. The screen uses a 40% minimum deviation and a 3-sigma band; a different dataset might want different values. There is a config file for exactly that.

## Links

- **Code Repository:** https://github.com/ANSUJKMEHER/Napper
- **Live Demo Page:** https://ansujkmeher.github.io/Napper/
- **Demo Video:** {{VIDEO_LINK}} (YouTube / Loom)
- **Agent Handoff & Session Logs:** Documented in [context.md](https://github.com/ANSUJKMEHER/Napper/blob/main/context.md) and [PLAN.md](https://github.com/ANSUJKMEHER/Napper/blob/main/PLAN.md)

## Team

- **Ansuj Kumar Meher** ([@ansujkmeher](https://dev.to/ansujkmeher) / [@ANSUJKMEHER](https://github.com/ANSUJKMEHER))

## Prize categories

Best Use of TabPFN, Best Use of Gemma, Best Use of Sentry Agent Tracing, Best Use of Entire.

#devchallenge #hf26challenge
