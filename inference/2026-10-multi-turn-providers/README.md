# Multi-turn provider comparison, October 2026

Part of the [inference benchmarks](../README.md). This run compared the same three model families on Telnyx, Baseten, Together AI and Fireworks across 15 fixed multi-turn scenarios.

| Model | Telnyx p50 conversation time | Next fastest | Telnyx observed p95 | Next fastest |
|---|---:|---:|---:|---:|
| GLM 5.3 Flash | 8.26 s | 11.00 s | 35.62 s | 42.72 s |
| GLM 5.3 | 13.48 s | 15.85 s | 41.33 s | 50.65 s |
| Kimi K3 | 10.49 s | 15.95 s | 46.40 s | 49.66 s |

The benchmark attempted 540 conversations and completed 530. Quality, objective checks, reliability, first-answer latency and completed-conversation latency had different leaders; there is no weighted overall winner.

Read [`report/REPORT.md`](report/REPORT.md) for the complete provider/model tables and limitations. The public article is [Multi-turn LLM benchmark: 3 models, 4 providers](https://telnyx.com/resources/multi-turn-llm-benchmark).

## Layout

| Path | What it is |
|---|---|
| `report/` | Full report and Telnyx-branded charts |
| `data/turns.csv` | Per-turn prompts, visible answers, timings and token counts |
| `data/conversations.csv` | One row per attempted conversation |
| `data/judges.csv` | Blind quality scores, completion decisions and rationales |
| `data/objective-checks.csv` | Deterministic checks and outcomes |
| `data/provider_model_summary.csv` | Canonical provider/model aggregates |
| `data/failure_summary.csv` | Failed conversations by provider and model |
| `config/` | Scenario, provider/model, judge and run configuration |
| `scripts/` | Launch, export, summarization and chart-generation scripts |

## Read before quoting

- One automated judge evaluated the first successful repeat for each provider/model/scenario cell. Small quality differences are directional.
- The scenarios are synthetic and do not use live tools, retrieval or external APIs.
- All providers were called from the same Telnyx Stateful Actor using explicit visible conversation history.
- Observed p95 values use 40–45 completed conversations per provider/model cell and are not SLAs.
- Hidden reasoning was not added to later turns and is omitted from this public export.

## Disclosure

Run by Telnyx staff from October 7–8, 2026. Telnyx Inference was one of the four compared providers. The benchmark actor was the common request origin for all providers.
