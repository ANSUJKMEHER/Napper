# Napper — build plan (Hacktoberfest Open-Source AI Challenge: Week 3)

Theme: **Slow and Steady** (rewards laziness; International Sloth Day was Oct 20).
Prompt: build something with open-source AI at its core and explain why open innovation matters.

## The bet

One project, entered in several partner categories. The FAQ says a submission is
automatically in the running for the overall prize ($250) and every partner category it
qualifies for, but **you can win only once per challenge**. DEV's own Pro Tip: partner
category winners come from a smaller pool, so the odds are meaningfully higher.

Primary target: **Best Use of TabPFN (featured, $200)**. Field intel from current Week 3
entries: `nightshift` (chat digest + self-check), `slothd` (workspace tidier), `SlothQA`
(UI regression agent), `Doze` (payment reconciliation). All of them are local-LLM
wrappers. Nobody is doing forecasting/prediction. A tabular forecasting agent is the
differentiated lane, and Prior Labs says they favor exactly that archetype ("TabPFN
inside a wider prediction agent").

## Prize categories to enter (in the post)

| Category | Prize | Effort | Status |
|---|---|---|---|
| Best Use of TabPFN | $200 | core of the build | in code, needs real-device run |
| Best Use of Gemma | $200 | Ollama + gemma3 | code ready, needs Ollama run |
| Best Use of Sentry Agent Tracing | $100 | half-day instrumentation | not started |
| Best Use of Entire | $100 | share agent sessions | not started (do at build time) |
| Best Use of a .tech Domain | $100 | claim free promo domain, host demo page | not started (claim today) |
| Best Use of Temporal | $100 | durable workflow (skeleton written) | only if actually run |

Skip: Render/DigitalOcean (cloud hosting contradicts the offline story), Tinker
(fine-tuning too heavy for 3.5 days), Arduino (no board), and the rest (badge-stuffing
dilutes the write-up).

## Team board (max 4 listed; extras are unlisted support)

- **P1 — Forecaster:** run TabPFN on a real machine; license acceptance; verify the
  recursive horizon; baseline comparison table; anomaly tuning.
- **P2 — Harness:** Ollama + Gemma digest runs; airplane-mode demo; cron setup;
  Temporal v2 only if time allows.
- **P3 — Platform:** GitHub repo (created in-window, clean commits), Sentry tracing,
  .tech domain + demo page, README, DevRelay/Entire agent-session capture.
- **P4 — Story:** demo video, tortoise-vs-hare experiment numbers, the DEV post
  (from `docs/POST_DRAFT.md`), reaction campaign (MLH Discord, socials).

Support roles (unlisted): QA of scripts on Windows/macOS, data redaction checks,
video editing.

## Day-by-day (IST)

- **Thu Oct 22:** claim promos at hacktoberfest.com/my/promos (.tech domain, credits);
  accept TabPFN license at platform.priorlabs.ai; create GitHub repo; first real TabPFN
  forecast on a real bank CSV (P1); Ollama + gemma3 digest hello-world (P2).
- **Fri Oct 23:** first full overnight run with real engines; screenshot artifacts;
  Sentry on (P3); tortoise-vs-hare numbers (P4).
- **Sat Oct 24:** demo video; .tech page; README; post draft finalized; publish by
  ~23:00 IST. Start the reaction campaign.
- **Sun Oct 26 before 12:29 IST:** buffer for fixes only. Deadline is 23:59 PDT Oct 25.

## Demo script (the five beats)

1. Drop 3 CSVs into `inbox/` and go to bed (screen recording, sped up).
2. Morning: `out/latest.md` shows the two-line digest.
3. The catches: gym price hike (24.99 -> 29.99), the forgotten Streamly subscription,
   the double electricity charge, the kWh spike — each with its screenshot.
4. Airplane mode: same run, zero internet, works. (Proves offline + privacy.)
5. Tortoise vs Hare table from `experiments/tortoise_vs_hare.py`: closed hosted API
   vs local TabPFN on cost, privacy, offline, error, latency. Fill in real hare numbers;
   never invent them.

## Write-up blueprint (writing quality is weighted most heavily)

Draft lives in `docs/POST_DRAFT.md`. Structure: hook -> sloth/laziness manifesto ->
what Napper is -> quantified lazy payoff -> tortoise vs hare -> why open matters
(offline / private / free / auditable-swappable) -> how it works (2 code snippets) ->
honest limitations -> demo + GitHub + agent session links -> prize categories entered.
Voice: first person, specific numbers, no hype adjectives, no em-dash abuse.

## Risks and gotchas

- TabPFN weights are non-commercial; say so in the post.
- TabPFN import is heavy (torch). Keep datasets <= ~5k rows on CPU.
- Repo must be created inside the challenge window; post-deadline commits must be noted in README.
- Teams capped at 4; one submission per team; list DEV handles in the post.
- Ties broken by reactions: publish early and farm them.
- Only one win per submission: depth of the TabPFN story matters more than the number of badges.

## Definition of done

- [ ] Real TabPFN-3.5 run on a dev machine, results JSON saved in `data/forecasts/`
- [ ] Real Gemma digest written at least once, screenshot in the post
- [ ] Tortoise-vs-hare table filled with real numbers
- [ ] Demo video + GitHub link + DevRelay session link in the post
- [ ] Post published with template tags `#devchallenge` `#hf26challenge` before the deadline

## Links

- Challenge page: https://dev.to/challenges/hacktoberfest-week3-2026-10-19
- Promos/credits: https://hacktoberfest.com/my/promos
- TabPFN docs: https://docs.priorlabs.ai/ — license: https://platform.priorlabs.ai
- TabPFN repo: https://github.com/PriorLabs/tabpfn
- Ollama: https://ollama.com — model: gemma3
