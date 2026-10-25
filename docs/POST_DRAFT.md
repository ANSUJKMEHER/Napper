*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 3: Slow and Steady](https://dev.to/challenges/hacktoberfest-week3-2026-10-19)*

---

## What I Built

I am lazy in a very specific way. Not the way where you skip work, but the way where you will spend an entire weekend automating a task that takes two minutes just so you never have to do it again. This project is that, plus an open-weight foundation model doing the two minutes.

The routine I kept dreading was checking stuff: open the banking app, scroll through the electricity bill, check my step count. Three apps, every morning, and every morning the same small disappointment: no surprises, just data. I did not want to check stuff anymore. I wanted the data to check itself and tell me only when it had something important to say.

So I built **Napper**: an offline-first, autonomous predictive AI agent that runs while you sleep.

### How It Works

You drop CSVs into a local folder and go to bed. Any CSV: a bank export, a smart-meter export, a fitness tracker, or utility readings. Somewhere between 3:00 AM and your alarm, Napper:

1. **Ingests & Normalizes:** Reads new files, normalizes timestamps and numeric series, and appends them to a local store. Duplicate drops are ignored by SHA-256 content hashing.
2. **Forecasts the Next Month:** Uses **TabPFN-3.5**, an open-weight tabular foundation model from Prior Labs that runs on your local CPU/GPU, to generate recursive 30-day forecasts with holdout validation.
3. **Screens for Anomalies:** Runs a model-free walk-forward seasonal screen (today vs. the median of the previous eight same-weekdays) so that one bad week doesn't poison future comparisons.
4. **Audits Transactions:** Scans bank transactions for recurring subscription creep, price hikes, and accidental same-day duplicate charges.
5. **Generates a Morning Brief:** Writes a concise morning brief — typically two lines per source, and on quiet mornings, almost nothing — delivered via text and text-to-speech audio.

### What It Caught on Demo Data (1,110 Points, 0 False Alarms)

I generated four synthetic CSVs (`bank`, `electricity`, `steps`, and `water`) with real-world storylines planted in them, seeded so anyone can reproduce the exact results. 

The digest from the TabPFN run (`out/latest.md`):

```
bank next month: ~1904.17 (local model tabpfn-3.5, holdout error 2.03%).
price change: fitness first gym was $24.99/mo, now $29.99/mo (+20%); possible duplicate charge: city power light billed 2x $77.86 on 2026-09-20; water spike: 425.0 liters on 2026-10-19 (expected ~52.8 liters, +706%)
```

Four catches across four distinct detectors:

- **Gym Membership Hike:** The gym quietly bumped its monthly fee from $24.99 to $29.99 (+20%). The recurring-charge detector clusters debits by merchant, determines monthly stability, and flags price drift.
- **Double Billing:** The power company accidentally charged twice on the same day for the exact same amount ($77.86 x2 on 2026-09-20). The duplicate detector isolates identical amounts from the same merchant on the same date without needing heavy ML.
- **3-Day Electricity Spike:** A 262% power surge in September (57.70 kWh vs. expected 15.95 kWh). The seasonal screen flagged all 3 spike days with 0 false alarms across the 386-day history.
- **Water Pipe Burst:** A catastrophic spike on October 19 where water usage surged to 425.0 liters/day against an expected baseline of 52.8 liters (+706%). Catching a plumbing burst on Day 1 saves hundreds in utility bills and prevents thousands in home flood damage.
- **Forgotten Subscription:** In the audit table, Napper surfaced *Streamly*, $9.99/month, 13 months running. Unused since March, but silently billing.

---

## Demo

{% youtube cplgL3_lUTw %}

- 🌐 **[Live Interactive Dashboard (GitHub Pages)](https://ansujkmeher.github.io/Napper/)**
- 🎬 **Direct Video Link:** [https://youtu.be/cplgL3_lUTw](https://youtu.be/cplgL3_lUTw)

### Dashboard & Audio Brief Features:
- **Audio Morning Brief:** Integrated Web Speech API reads aloud your morning forecast and catches at the click of a button (`🔊 Listen to Brief`).
- **Predictive Time-Series Studio:** Interactive Chart.js visualizer rendering observed history, 30-day TabPFN forecast horizons, and isolated anomaly markers in red.
- **Active Datasets Studio:** Granular per-dataset controls (`[⚡ Analyze]` single files, batch selection, instant chart switching via `[📈 Studio]`).
- **Drag-and-Drop Ingestion:** Drop CSVs directly into the browser to auto-hash, parse, and queue them for processing without touching the terminal.
- **Sentry Trace Waterfall:** Visual verification of all distributed pipeline spans with `$0.00` metered cost.

---

## Code

{% github ANSUJKMEHER/Napper %}

- **GitHub Repository:** [https://github.com/ANSUJKMEHER/Napper](https://github.com/ANSUJKMEHER/Napper)

### Quickstart (Run It Yourself in 60 Seconds)

```bash
git clone https://github.com/ANSUJKMEHER/Napper.git
cd Napper
python -m venv .venv
# On Windows: .venv\Scripts\activate | On macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Run the 2-second fast agent demo
python -m napper.cli demo

# Launch the interactive web studio & audio brief
python -m napper.cli web
# Open http://localhost:5000 in your browser
```

---

## How I Built It

Napper is an offline agent pipeline engineered around local open-weight foundation models and privacy-preserving observability:

### 1. TabPFN-3.5 Foundation Model (Prior Labs)
Rather than relying on brittle classical statistical ARIMA heuristics or cloud LLMs that hallucinate tabular numbers, Napper uses **TabPFN-3.5** as its predictive engine. TabPFN is an in-context learning transformer trained on synthetic tabular datasets that performs zero-shot regression without gradient descent at inference time.

Napper generates lag features (1, 2, 7, 14, 30 periods), calendar features (day of week, day of month, trend), fits TabPFN on the training history, and generates 30-day forecast horizons through recursive one-step autoregression:

```python
from tabpfn import TabPFNRegressor

reg = TabPFNRegressor(device="auto")
reg.fit(train[FEATURE_COLS], y_train)
horizon = recursive_forecast(reg, last_row, history, horizon_periods=30)
```

### 2. Sentry AI Agent Tracing ($0.00 Metered Observability)
Most AI agent tracing tools monitor expensive cloud API calls. Napper integrates **Sentry AI Agent Distributed Tracing** to track local execution with zero PII in the payloads:
- **Root Span:** `napper.overnight_run` (`op="ai.agent"`) tracks end-to-end runtime.
- **Tool Spans:** `ai.tool.ingest`, `ai.tool.recurring`, `ai.tool.duplicate`, and `ai.tool.anomaly_screen` record per-module latencies and detection counts.
- **Model Span:** `ai.model.tabpfn` records dataset shapes, holdout WMAPE, and inference timing.
- **Zero-Cost Measurement:** Every span explicitly tags `ai.cost = 0.0` and records `ai_cost_usd = 0.00`. It proves full distributed trace waterfalls across local silicon with **zero PII transmitted**.

### 3. Model-Free Seasonal Anomaly Screen
Foundation models forecast the future, but recent anomaly screening uses a robust, non-parametric median filter:

```python
def seasonal_expected(values, i, period_lag=7):
    # Median of previous 8 same-weekdays: one bad week never poisons the baseline
    pts = [values[i - period_lag * k] for k in range(1, 9) if i - period_lag * k >= 0]
    return float(np.median(pts))
```

### 4. Dual-Speed Execution Engine
- **Nap Mode (~2s):** Lightweight baseline for immediate CLI testing and rapid UI iteration.
- **Deep Sleep Mode (~373s):** Full TabPFN-3.5 foundation model execution designed to run overnight while you sleep ("Slow and Steady").

---

## Why Does Open Innovation Matter?

The prompt asks where an open-based approach worked better than a closed one. We ran a reproducible head-to-head benchmark comparing **Napper's local TabPFN-3.5** against a closed **GPT-4o-mini zero-shot prompt** on the exact same dataset (`experiments/hare_measure.py`, artifact at `data/hare/run.json`):

| Attribute | Hare (Closed Cloud API: `gpt-4o-mini`) | Tortoise (Napper: TabPFN-3.5 Local) |
|---|---|---|
| **Model Type** | Proprietary Cloud API (`gpt-4o-mini`) | **TabPFN-3.5 (Open Foundation Model)** |
| **Cost Per Run** | ~$0.0123 / run ($4.49 / yr cloud API tax) | **$0.00 (Zero runtime cost)** |
| **Data Privacy** | ❌ Bank statements transmitted over cloud | **✅ 100% Local (0 bytes transmitted)** |
| **Offline Capable** | ❌ Fails without active internet | **✅ Works in airplane mode / air-gapped** |
| **Daily Spend Holdout Error (WMAPE)** | 165.45% (Prompted zero-shot regression) | **56.34% (3x better than GPT-4o-mini, 12x vs naive)** |
| **Monthly Spend WMAPE** | 4.85% | **2.03%** |
| **Execution Latency** | ~3.42s (Network round-trip) | ~373s (Consumer AMD Ryzen CPU "Slow & Steady") |
| **Auditability & Portability** | ❌ Closed black box; vendor lock-in | **✅ Open weights, fully auditable, swappable** |

### Why Open Wins Here:
1. **Financial Privacy:** A bank statement is a personal autobiography. Sending personal financial debits to a commercial cloud API is a non-starter. Open models mean your financial life never leaves your machine.
2. **Tabular Precision vs. LLM Hallucination:** Prompted LLMs struggle with day-of-month and calendar arithmetic, yielding 165.45% error. TabPFN is specifically pretrained on tabular priors, beating GPT-4o-mini by **~3x**.
3. **Zero Recurring Cost:** Closed APIs tax you every night forever. Open weights run on consumer laptops you already own for **$0.00**.

---

## My Agent Session

Napper was designed and developed with autonomous agent workflows and systematic planning:
- **Architecture & Progress Tracking:** Documented in [`PLAN.md`](https://github.com/ANSUJKMEHER/Napper/blob/main/PLAN.md) and [`context.md`](https://github.com/ANSUJKMEHER/Napper/blob/main/context.md).
- **Verified Test Suite:** 16 automated unit tests validating ingestion deduplication, anomaly math, recurring charge clustering, and API contract fidelity (`tests/test_server.py`).
- **Reproducible Experiments:** The complete benchmark script and raw JSON runs comparing TabPFN to cloud APIs are published in `experiments/hare_measure.py` and `data/hare/run.json`.

---

## The Lazy Payoff

The contest asks for the effort saved. Here is the arithmetic for *what each catch is worth* — if Napper is watching when one of these happens:

- **Mental Tax Saved:** Checking 3 apps each morning takes ~2 minutes of scrolling. Reading a 10-second brief saves ~1.5 hours a month of friction.
- **Economic Value ($948+ Annual Protection):**
  - **Water Pipe Burst Caught:** A +706% surge caught on Day 1 prevents hundreds in utility bills and thousands in home flood damage ($450+ avoided).
  - **Price Hike Defense:** Caught the gym's silent $5/month increase ($60/yr avoided).
  - **Duplicate Billing Defense:** Caught a $77.86 double power charge immediately ($77.86 recovered).
  - **Zero SaaS Fees:** Typical commercial SaaS anomaly and time-series monitoring tools cost roughly $30/month ($360/yr saved). Napper costs $0.00.

### Honest Limitations & Disclosures:
- **Hardware Latency:** On our test laptop (AMD Ryzen 5 5625U CPU, 16GB RAM), multi-series TabPFN-3.5 inference takes ~6 minutes (~373s, "Slow and Steady"). On an NVIDIA GPU, it runs in seconds.
- **Licensing:** TabPFN-3.5 weights are released under a non-commercial research license.
- **Gemma Local Bridge:** The recorded demo runs the deterministic brief writer. The Gemma bridge is implemented in `napper/digest.py`, fully unit-tested, and activates automatically when Ollama is running.

---

## Prize Categories

- **Best Use of TabPFN:** Primary entry. TabPFN-3.5 foundation model powers the predictive time-series core with 2.03% holdout error, benchmarked against GPT-4o-mini.
- **Best Use of Sentry Agent Tracing:** Complete distributed trace waterfall across agent tools, models, and anomaly screens with `$0.00` cost tagging and 0-byte PII leakage.
- **Best Use of Gemma:** Natural language morning brief generation bridge via Ollama (`napper/digest.py`).
- **Best Use of Entire:** Agent-session transparency: [PLAN.md](https://github.com/ANSUJKMEHER/Napper/blob/main/PLAN.md) and [context.md](https://github.com/ANSUJKMEHER/Napper/blob/main/context.md) document the full autonomous agent trajectory (see My Agent Session).

---

## Team

- **Ansuj Kumar Meher** ([@ansujkmeher](https://dev.to/ansujkmeher) / [@ANSUJKMEHER](https://github.com/ANSUJKMEHER))

---
*Tags: #devchallenge #hf26challenge #python #ai*