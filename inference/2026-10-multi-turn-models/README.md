# Multi-turn model comparison, October 2026

Part of the [inference benchmarks](../README.md). This run compared GLM 5.3 Flash, GLM 5.3 and Kimi K3 on 15 fixed multi-turn scenarios served by Telnyx Inference.

| Model | Completed conversations | Objective checks | p50 conversation response time | Observed p95 |
|---|---:|---:|---:|---:|
| GLM 5.3 Flash | 15/15 | 22/28 | 8.35 s | 31.27 s |
| GLM 5.3 | 15/15 | 23/28 | 16.38 s | 53.19 s |
| Kimi K3 | 15/15 | 23/28 | 9.36 s | 55.71 s |

Conversation response time is the sum of model-response latency across the fixed turns; it excludes user pauses. Quality, completion, objective checks and latency are reported separately rather than combined into one winner.

Read [`report/REPORT.md`](report/REPORT.md) for the full results. The public article is [We tested 3 open-weight models for multi-turn agents](https://telnyx.com/resources/choose-open-weight-model).

## Layout

| Path | What it is |
|---|---|
| `report/` | Report and publication charts |
| `data/turns.csv` | Per-turn timing, token counts, prompts and visible answers |
| `data/conversations.csv` | One row per model/scenario conversation |
| `data/judges.csv` | Blind judge scores and rationales, with raw response envelopes removed |
| `data/objective-checks.csv` | Deterministic checks and outcomes |
| `config/` | Scenario, model, judge and run configuration |
| `scripts/` | Runner, rejudge, summarization and chart scripts |

## Read before quoting

- The scenarios are synthetic, conversation-only and do not use live tools or retrieval.
- Two automated judges evaluated every completed conversation; this was not human evaluation.
- Observed p95 uses 15 conversations per model and is sample-specific, not an SLA.
- Hidden model reasoning is excluded from this public package. Visible answers remain so deterministic checks can be audited.

## Disclosure

Run by Telnyx staff on October 5, 2026. All three candidate models and both blind judges were served through Telnyx Inference. Benchmark execution used a Telnyx Stateful Actor with explicit conversation history.
