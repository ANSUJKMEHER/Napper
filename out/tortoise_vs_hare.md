# Tortoise vs Hare

Measured comparison between closed hosted AI (GPT-4o-mini zero-shot prompted forecast) and Napper's local open stack (TabPFN-3.5 foundation model). Benchmark artifact and reproducible code available at `experiments/hare_measure.py` and `data/hare/run.json`.

| Attribute | Hare (Closed Hosted API: GPT-4o-mini) | Tortoise (Napper: TabPFN-3.5 Local) |
|---|---|---|
| **Model Type** | Proprietary Cloud API (gpt-4o-mini (Zero-Shot Prompted)) | tabpfn-3.5 (Open-Weight Foundation Model) |
| **Cost Per Run** | ~$0.0123 / run ($4.49 / yr) | **$0.00 (Zero runtime cost)** |
| **Data Privacy** | ❌ Data leaves machine (bank transactions sent over cloud) | **✅ 100% Local (0 bytes transmitted)** |
| **Offline Capable** | ❌ Fails without active internet connection | **✅ Works in airplane mode / air-gapped** |
| **Holdout Error (Daily Spend WMAPE)** | 165.45% (Prompted zero-shot token regression) | **56.34% (3x better than GPT-4o-mini, 12x better than naive)** |
| **Monthly Spend WMAPE** | 4.85% | **2.03%** |
| **Execution Latency** | ~3.42s (Network API round-trip) | ~373s (Local AMD Ryzen CPU "Slow & Steady") |
| **Auditability & Portability** | ❌ Closed black box; subject to vendor deprecation | **✅ Open weights, fully auditable, swappable** |
