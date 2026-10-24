# Tortoise vs Hare

| Attribute | Hare (Closed Hosted API: GPT-4o-mini / Hosted Forecast) | Tortoise (Napper: TabPFN-3.5 Local) |
|---|---|---|
| **Model Type** | Proprietary Cloud API | TabPFN-3.5 (Open-Weight Foundation Model) |
| **Cost Per Run** | ~$0.012 / run (token usage & cloud fees) | **$0.00 (Zero runtime cost)** |
| **Data Privacy** | ❌ Data leaves machine (bank transactions sent over cloud) | **✅ 100% Local (0 bytes transmitted)** |
| **Offline Capable** | ❌ Fails without active internet connection | **✅ Works in airplane mode / air-gapped** |
| **Holdout Error (Daily Spend WMAPE)** | 62.40% (Prompted zero-shot token regression) | **56.34% (12x improvement over 676.78% naive baseline)** |
| **Monthly Spend WMAPE** | 4.85% | **2.03%** |
| **Execution Latency** | ~3.4s (Network API round-trip) | ~432s (Local AMD Ryzen CPU "Slow & Steady") |
| **Auditability & Portability** | ❌ Closed black box; subject to vendor deprecation | **✅ Open weights, fully auditable, swappable** |
