# GLM 5.3 Flash: Telnyx and Modal Shared, October 2026

Part of the [inference benchmarks](../README.md). This run compared `zai-org/GLM-5.3-Flash` on Telnyx Inference and Modal Shared, two managed pay-per-token endpoints.

| Metric | Telnyx Inference | Modal Shared |
|---|---:|---:|
| Successful fresh requests | 240/240 | 240/240 |
| Pooled p50 completed-response latency | 4.92 s | 8.75 s |
| Pooled p95 completed-response latency | 11.91 s | 20.62 s |
| Pooled p50 output speed | 138.1 tok/s | 66.2 tok/s |
| Estimated list-price cost | $2.20 | $7.34 |

Telnyx had lower median completed-response latency and higher median output speed in all eight fresh workload/concurrency cells. Modal Shared had lower p95 time to first visible answer in seven of eight cells.

Read [`report/REPORT.md`](report/REPORT.md) for the complete cell-level results. The public article is [GLM 5.3 Flash benchmark: Telnyx vs Modal](https://telnyx.com/resources/glm53-flash-benchmark).

## Layout

| Path | What it is |
|---|---|
| `report/` | Full standalone report and publication charts |
| `data/raw-measurements.csv` | All warm-up, fresh, cache-seed and shared-prefix rows with text traces removed |
| `data/clean-successful-requests.csv` | Successful rows used for latency summaries |
| `data/summary.csv` | Profile, concurrency and cache-mode aggregates |
| `data/cost_summary.csv` | Token-based list-price estimates |
| `config/` | Sanitized endpoint settings, pricing snapshot and model-availability snapshot |
| `scripts/` | Runner, exporter, summarizer and shared benchmark library |

## Read before quoting

- The primary comparison is Telnyx Inference versus Modal Shared. Modal Dedicated was not tested.
- Concurrency 1 and 10 were tested. Modal Shared's tested account limit prevented a valid concurrency 50 or 100 comparison.
- Neither API reported cached-token evidence. Shared-prefix phases are preserved, but no cache-hit claim is made.
- Costs are measured token counts multiplied by published list prices, not reconciled invoices.
- Managed endpoint cold starts could not be forced or isolated.

## Disclosure

Run by Telnyx staff from a Telnyx Stateful Actor on October 12–13, 2026. Telnyx Inference was one of the compared endpoints. Both endpoints received the same prompts, settings and request schedule from the same benchmark environment.
