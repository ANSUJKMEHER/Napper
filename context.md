# Napper — project context (agent handoff doc)

> **For:** any AI agent or teammate continuing this work in a later session.
> Read this file first, then `PLAN.md`, then `docs/POST_DRAFT.md`, then the code.
> Update the "Current state" section before you end your own session.

## Mission (one line)

Ship a Hacktoberfest Week 3 "Slow and Steady" entry: **Napper**, a local, offline-first
agent that turns CSVs you drop into a folder into a two-line morning digest, powered by
open-weight models (TabPFN-3.5 for forecasting, Gemma for the digest), plus a great DEV
post to go with it.

## Deadline and timezone

- Submissions due: **Oct 25, 2026 11:59 PM PDT = Oct 26, 2026 12:29 PM IST**.
- Plan: publish by **Sat Oct 25, ~23:00 IST** for a reaction buffer (reactions break judge ties).
- Repo and commits must sit inside the challenge window (Oct 19–25, 2026 PDT).
  Commits made after the deadline must be noted in the repo README (contest rule).
- Team is capped at **4 people** listed on the post. Extra helpers do unlisted support work.

## Where things live

- Workspace folder: `General/napper/` (Team Space, so every teammate can see it).
- `context.md` — status, decisions, handoff. You are reading it.
- `PLAN.md` — full strategy, category targets, 4-person board, day-by-day timeline, demo script.
- `docs/POST_DRAFT.md` — the DEV write-up draft (writing quality is the most heavily weighted criterion).
- `README.md` — GitHub-facing readme (repo must be created by the team inside the challenge window).
- Code: `napper/` package + `scripts/`, `experiments/`, `scheduler/`, `tests/`.

## Current state (updated 2026-10-24 ~22:35 IST by Antigravity)

- [x] Project skeleton + full core pipeline written and working
- [x] End-to-end demo verified with the 3 sample CSVs (naive fallback engine, template digest)
- [x] Demo catches all three planted storylines: gym price hike +20%, power double charge
      (2x $77.86 on 2026-09-20), 3-day kWh spike (+262%) — and nothing else (0 noise flags)
- [x] Full unit test suite passing (12 tests across ingest, recurring, anomaly, tracing, and web server endpoints)
- [x] `tabpfn` package installed in `.venv` (Python 3.11 + PyTorch 2.14). Graceful degradation to naive
      working and verified; TabPFN-3.5 token and weights loaded locally.
- [x] Sentry Agent Tracing implemented (`napper/tracing.py`) with zero-cost ($0.00) tracking, span
      hierarchy, and automatic fallback when unconfigured.
- [x] Public GitHub repo created inside challenge window: `https://github.com/ANSUJKMEHER/Napper`
      and initial codebase pushed to `main`.
- [x] Interactive web demo built (`docs/index.html`) with canvas time series visualizer, catches cards,
      comparison matrix, and GitHub Pages enabled at `https://ansujkmeher.github.io/Napper/`.
- [x] Built-in Interactive Local Web Dashboard implemented (`napper/server.py` and `napper/web/index.html`)
      running on `http://localhost:5000` via `python -m napper.cli web` featuring:
      - Drag-and-drop CSV ingestion
      - Dual-speed execution toggle: ⚡ Nap Mode (~2s) vs 🦥 Deep Sleep Mode (TabPFN-3.5)
      - Interactive Chart.js time-series & forecast visualizer
      - Text-to-speech audio morning brief synthesis
      - Sentry Agent Tracing waterfall view ($0.00 cost)
- [x] `docs/POST_DRAFT.md` updated with real TabPFN-3.5 metrics, Sentry tracing section, web UI section, and live links.
- [x] Tortoise-vs-hare comparison script working
- [x] TabPFN-3.5 first fit and weights download completed on local machine! Real open weights
      running 100% offline, predicting next month spend at ~1904.17 (2.03% holdout error) and
      daily spend holdout at 56.34% (vs 676.78% naive baseline).
- [ ] Demo video recording & post publication on DEV.to

## Demo numbers (from verified real TabPFN-3.5 run)

```
bank next month: ~1904.17 (local model tabpfn-3.5, holdout error 2.03%).
price change: fitness first gym was $24.99/mo, now $29.99/mo (+20%); possible duplicate
charge: city power light billed 2x $77.86 on 2026-09-20; 2026-09-16: 57.70 vs expected
15.95 (+262%)
```

Real engine metrics across series:
- bank monthly spend: TabPFN-3.5 WMAPE 2.03% (naive baseline 1.77%)
- bank daily spend diagnostic: TabPFN-3.5 WMAPE 56.34% (naive baseline 676.78%, 12x improvement)
- electricity (kWh): TabPFN-3.5 WMAPE 21.96% (naive baseline 19.62%), 3 planted spikes flagged
- steps: TabPFN-3.5 WMAPE 9.53% (naive baseline 12.83%, TabPFN beats baseline by 3.3%)
All 3 planted events caught with zero false alarms.

## How to run

```bash
cd General/napper
python -m pip install -r requirements.txt        # pandas, numpy, requests
python -m napper.cli demo                        # generate 3 sample CSVs into inbox/ + run the whole pipeline
python -m napper.cli run                         # one overnight run (ingest -> forecast -> anomalies -> digest)
python -m napper.cli watch --minutes 60          # loop; v1 scheduler is cron: 0 3 * * * python -m napper.cli run
python -m pytest tests -q                        # run tests (pip install pytest first)
python -m experiments.tortoise_vs_hare --data data/store/bank.csv   # closed-vs-open table
```

Outputs: normalized CSVs in `data/store/`, run results in `data/forecasts/run-*.json`,
digest history in `out/digest.md`, latest digest in `out/latest.md`, comparison table in
`out/tortoise_vs_hare.md`. Generated artifacts are reproducible: delete `data/`, `out/*.md`,
`inbox/*.csv`, `inbox/processed/` and re-run `demo` for a clean slate.

Real engine (dev machine): `pip install tabpfn` (heavy, needs torch). Accept the TabPFN-3.5
non-commercial license once; weights download on first `fit()`, then everything runs offline.
Real digest: install Ollama, `ollama pull gemma3`, keep Ollama running on localhost:11434.

## Architecture

```
inbox/*.csv  ->  ingest (normalize, dedupe by content hash)  ->  data/store/{dataset}.csv
store        ->  series: monthly spend (bank-like data) or daily numeric columns (kwh, steps)
series       ->  forecast: TabPFN-3.5 on calendar + lag features, recursive horizon;
                 naive linear-detrended baseline always computed alongside
series       ->  walk-forward anomaly screen: today vs median of prior 8 same weekdays,
                 3-sigma robust band, >=40% off (model-free, labels not needed)
store        ->  recurring-charge detection: merchants in >=3 months; only "stable" merchants
                 (monthly CV <= 10%) can raise price-change alerts
store        ->  duplicate-charge detection: same (day, merchant, amount) seen >= 2x
results      ->  digest: Gemma via Ollama, or deterministic template fallback  ->  out/digest.md
```

## Key decisions and why

1. **TabPFN-3.5 as the core brain.** Featured partner category, $200, tiny entry pool
   (DEV's own tip: partner pools are smaller = better odds). Prior Labs explicitly favors
   "TabPFN inside a wider prediction agent", which is exactly Napper. Most Hacktoberfest
   entrants build LLM chat wrappers; a forecasting agent stands out.
2. **Gemma (Ollama) writes the digest.** Second featured $200 ticket, and it makes the
   "local open model" story real. Template fallback keeps the pipeline working anywhere.
3. **Offline-first, $0 runtime.** That is the "why open matters" narrative: airplane-mode
   demo, bank CSVs never leave the machine, no API bill, models are swappable/auditable.
4. **Spend is forecast monthly, not weekly or daily.** Weekly spend is bimodal (rent week
   vs no-rent week) and daily spend is mostly zeros plus a rent spike; both wreck naive
   baselines and holdout metrics. Monthly totals are stationary and sane (holdout 1.77%).
   A daily diagnostic series is added automatically when TabPFN is installed, because a
   tabular model can learn day-of-month patterns the naive baseline cannot. The final
   month is dropped if incomplete so the holdout compares full months.
5. **Anomaly screen is model-free and seasonal.** Today vs median of the previous 8 same
   weekdays (median, not mean: outliers must not poison the expectation), robust MAD band,
   40% minimum deviation. On the demo data it flags exactly the 3 planted spike days.
   Spend gets no walk-forward screen: monthly bills drift across weekdays (rent lands on a
   different weekday every month), which breaks same-weekday logic; the recurring and
   duplicate detectors own that territory instead. Documented in the write-up as a
   deliberate limitation.
6. **Recurring-charge detection separates stable from variable merchants.** Only merchants
   whose monthly amounts vary little (CV <= 10%) can raise price-change alerts, so coffee
   and power bills do not pollute the digest. The forgotten-subscription catch is the
   recurring table itself (Streamly), which the human reviews; the agent never cancels
   anything.
7. **Demo data is seeded for a clean story.** Seeds 62 (electricity) and 64 (steps) were
   scanned so the only screen flags are the planted spike; bank uses seed 7. Do not change
   the seeds without re-verifying the demo output.
8. **Graceful degradation.** Every optional dependency (tabpfn, torch, Ollama) has a
   working fallback, so the pipeline never dies on a machine that lacks one of them.
9. **Categories to enter in the post:** Best Use of TabPFN, Best Use of Gemma,
   Best Use of Sentry Agent Tracing, Best Use of Entire, Best Use of a .tech Domain,
   Best Use of Temporal (only if the Temporal v2 path is actually built and run).
   Rule: one submission can win only once, but it is in the running for overall + every
   category it qualifies for. Use each partner meaningfully; don't badge-stuff.

## Gotchas for the next agent

- TabPFN weights are **non-commercial licensed**; state that in the post. Accept the
  license at platform.priorlabs.ai before the first `fit()`, or set `TABPFN_TOKEN`.
- TabPFN on CPU is fine up to ~5k samples; our demo series are ~390 daily points.
- If TabPFN errors at runtime, the code falls back to naive and labels the model
  `tabpfn-error(...)` in the result JSON. Do not ship that silently; investigate.
- Ollama must be running on localhost:11434 for the Gemma digest; otherwise digest_writer
  = "template". Both paths are legitimate demo outputs.
- **pandas 3.x string dtype gotcha:** `pd.read_csv` returns text columns as `str` dtype,
  not `object`. Column discovery uses `pd.api.types.is_string_dtype`, not `dtype == object`.
- The `data/` and `out/` folders are intentionally NOT gitignored, so judges can see the
  sample data, forecasts, and digest history in the repo.
- Repo must be created inside the challenge window; post-deadline commits must be noted
  in the repo README.
- Ties are broken by positive reactions on the DEV post: publish early, share on the MLH
  Discord and socials.
- One win per submission max; overall + partner categories share the same ticket.
- All numbers currently in `docs/POST_DRAFT.md` come from the naive fallback. Fill the
  `{{PLACEHOLDERS}}` with real TabPFN and closed-API measurements before publishing.
  Never invent the hare numbers.

## Handoff checklist (update before ending a session)

- Tick/untick the "Current state" checkboxes to match reality.
- Record any new decision + why.
- Record changed commands, new files, or new gotchas.
- If you ran the pipeline, paste the latest `out/latest.md` content into the demo
  numbers section and refresh any numbers quoted in `docs/POST_DRAFT.md`.
