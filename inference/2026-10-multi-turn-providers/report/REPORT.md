# Inter-provider multi-turn task completion benchmark

This report compares the same three model families across Telnyx, Baseten, Together AI, and Fireworks. Quality, completion, reliability, and latency are reported separately; there is no weighted overall score.

## Interpretation

- **Telnyx led or tied for GLM 5.3 Flash in:** Judge completion, Median total response time, Observed p95 total response time, Median per-turn E2E.
- **Telnyx led or tied for GLM 5.3 in:** Blind quality, Judge completion, Reliability, Median total response time, Observed p95 total response time, Median per-turn E2E.
- **Telnyx led or tied for Kimi K3 in:** Judge completion, Reliability, Median total response time, Observed p95 total response time, Median time to first answer, Median per-turn E2E.
- **Observed failed conversations:** Together AI: 6, Fireworks: 2, Baseten: 1, Telnyx: 1.
- **Blind quality scores ranged from 4.79 to 5.00 and came from one judge.** Treat small differences as directional rather than decisive.
- **There is no weighted overall winner.** Quality, completion, reliability, and latency should be read separately.

## Summary table

| Model | Provider | Successful conversations | Blind quality /5 | Judge completion | Objective checks | p50 conversation latency | p95 conversation latency | p50 TTFT latency | p50 TTFA latency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GLM 5.3 Flash | Telnyx | 44/45 | 4.90 (n=14) | 100.0%* | 77.8% | 8.26s* | 35.62s* | 0.37s | 0.46s |
| GLM 5.3 Flash | Baseten | 45/45 | 4.80 (n=15) | 93.3% | 78.6% | 12.56s | 71.03s | 0.35s | 0.55s |
| GLM 5.3 Flash | Together AI | 45/45 | 5.00 (n=15) | 100.0% | 78.6% | 11.00s | 42.72s | 0.25s | 0.42s |
| GLM 5.3 Flash | Fireworks | 45/45 | 4.92 (n=15) | 100.0% | 78.6% | 13.44s | 45.11s | 0.66s | 0.89s |
| GLM 5.3 | Telnyx | 45/45* | 4.95 (n=15)* | 100.0%* | 81.0% | 13.48s* | 41.33s* | 0.42s | 0.55s |
| GLM 5.3 | Baseten | 45/45 | 4.88 (n=15) | 100.0% | 79.8% | 15.85s | 50.65s | 1.46s | 1.79s |
| GLM 5.3 | Together AI | 44/45 | 4.87 (n=15) | 93.3% | 81.5% | 30.75s | 181.20s | 0.24s | 0.46s |
| GLM 5.3 | Fireworks | 43/45 | 4.88 (n=15) | 100.0% | 81.0% | 30.03s | 118.83s | 0.71s | 1.21s |
| Kimi K3 | Telnyx | 45/45* | 4.91 (n=15) | 100.0%* | 76.2% | 10.49s* | 46.40s* | 0.39s* | 0.54s* |
| Kimi K3 | Baseten | 44/45 | 4.96 (n=15) | 100.0% | 79.5% | 15.95s | 49.66s | 0.50s | 0.80s |
| Kimi K3 | Together AI | 40/45 | 4.79 (n=14) | 92.9% | 77.8% | 35.69s | 295.93s | 0.59s | 1.14s |
| Kimi K3 | Fireworks | 45/45 | 4.92 (n=15) | 100.0% | 78.6% | 44.48s | 115.36s | 1.47s | 2.34s |

\* Telnyx led or tied for the lead within that model family.

Conversation latency is the total model response time across all turns in the fixed multi-turn conversation. It sums per-turn E2E model response time and excludes user pauses. TTFT is time to first model activity; TTFA is time to first visible answer content. Latency percentiles include successful conversations only.

## Token usage per completed conversation

| Model | Provider | Mean input tokens | Mean output tokens | Mean total tokens |
| --- | --- | --- | --- | --- |
| GLM 5.3 Flash | Telnyx | 3093 | 1837 | 4930 |
| GLM 5.3 Flash | Baseten | 3076 | 1880 | 4957 |
| GLM 5.3 Flash | Together AI | 2960 | 1759 | 4719 |
| GLM 5.3 Flash | Fireworks | 2843 | 1720 | 4563 |
| GLM 5.3 | Telnyx | 3284 | 2034 | 5318 |
| GLM 5.3 | Baseten | 3309 | 2115 | 5424 |
| GLM 5.3 | Together AI | 3358 | 2097 | 5455 |
| GLM 5.3 | Fireworks | 3389 | 2111 | 5500 |
| Kimi K3 | Telnyx | 3389 | 1918 | 5307 |
| Kimi K3 | Baseten | 3356 | 1890 | 5245 |
| Kimi K3 | Together AI | 3340 | 1824 | 5164 |
| Kimi K3 | Fireworks | 3304 | 1795 | 5099 |

## Per-turn latency

| Model | Provider | Turns | p50 TTFT | p50 TTFA | p95 TTFA | p50 E2E | p95 E2E |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GLM 5.3 Flash | Telnyx | 176 | 0.37s | 0.46s | 1.26s | 1.85s | 9.14s |
| GLM 5.3 Flash | Baseten | 180 | 0.35s | 0.55s | 2.24s | 3.28s | 17.23s |
| GLM 5.3 Flash | Together AI | 180 | 0.25s | 0.42s | 1.33s | 2.62s | 12.76s |
| GLM 5.3 Flash | Fireworks | 180 | 0.66s | 0.89s | 2.70s | 3.39s | 12.80s |
| GLM 5.3 | Telnyx | 180 | 0.42s | 0.55s | 2.06s | 2.79s | 12.93s |
| GLM 5.3 | Baseten | 180 | 1.46s | 1.79s | 3.73s | 4.02s | 14.25s |
| GLM 5.3 | Together AI | 176 | 0.24s | 0.46s | 42.33s | 4.58s | 47.67s |
| GLM 5.3 | Fireworks | 172 | 0.71s | 1.21s | 22.01s | 7.00s | 35.27s |
| Kimi K3 | Telnyx | 180 | 0.39s | 0.54s | 3.29s | 2.57s | 10.71s |
| Kimi K3 | Baseten | 176 | 0.50s | 0.80s | 4.34s | 3.81s | 14.07s |
| Kimi K3 | Together AI | 160 | 0.59s | 1.14s | 40.00s | 6.07s | 77.06s |
| Kimi K3 | Fireworks | 180 | 1.47s | 2.34s | 10.39s | 11.12s | 33.65s |

## Category leaders

| Model | Category | Provider | Result |
| --- | --- | --- | --- |
| GLM 5.3 Flash | Blind quality | Together AI | 5.00 |
| GLM 5.3 Flash | Judge completion | Telnyx, Together AI, Fireworks | 100.0% |
| GLM 5.3 Flash | Objective checks | Baseten, Together AI, Fireworks | 78.6% |
| GLM 5.3 Flash | Reliability | Baseten, Together AI, Fireworks | 100.0% |
| GLM 5.3 Flash | Median total response time | Telnyx | 8.26s |
| GLM 5.3 Flash | Observed p95 total response time | Telnyx | 35.62s |
| GLM 5.3 Flash | Median time to first answer | Together AI | 0.42s |
| GLM 5.3 Flash | Median per-turn E2E | Telnyx | 1.85s |
| GLM 5.3 | Blind quality | Telnyx | 4.95 |
| GLM 5.3 | Judge completion | Telnyx, Baseten, Fireworks | 100.0% |
| GLM 5.3 | Objective checks | Together AI | 81.5% |
| GLM 5.3 | Reliability | Telnyx, Baseten | 100.0% |
| GLM 5.3 | Median total response time | Telnyx | 13.48s |
| GLM 5.3 | Observed p95 total response time | Telnyx | 41.33s |
| GLM 5.3 | Median time to first answer | Together AI | 0.46s |
| GLM 5.3 | Median per-turn E2E | Telnyx | 2.79s |
| Kimi K3 | Blind quality | Baseten | 4.96 |
| Kimi K3 | Judge completion | Telnyx, Baseten, Fireworks | 100.0% |
| Kimi K3 | Objective checks | Baseten | 79.5% |
| Kimi K3 | Reliability | Telnyx, Fireworks | 100.0% |
| Kimi K3 | Median total response time | Telnyx | 10.49s |
| Kimi K3 | Observed p95 total response time | Telnyx | 46.40s |
| Kimi K3 | Median time to first answer | Telnyx | 0.54s |
| Kimi K3 | Median per-turn E2E | Telnyx | 2.57s |

## Failure breakdown

| Model | Provider | Failed | Failure rate | Observed causes |
| --- | --- | --- | --- | --- |
| GLM 5.3 Flash | Telnyx | 1/45 | 2.2% | HTTP 503 provider error: 1 |
| GLM 5.3 | Together AI | 1/45 | 2.2% | No visible answer content: 1 |
| GLM 5.3 | Fireworks | 2/45 | 4.4% | No visible answer content: 1; Status unknown stream error: 1 |
| Kimi K3 | Baseten | 1/45 | 2.2% | HTTP 500 provider error: 1 |
| Kimi K3 | Together AI | 5/45 | 11.1% | HTTP 500 provider error: 2; No visible answer content: 2; Status unknown stream error: 1 |

## Methodology

- Dataset: `multi-turn-task-completion-inter-provider-v1` with 15 fixed multi-turn scenarios.
- Each provider/model cell ran each scenario three times. Blind judging was performed on successful repeat-1 conversations by DeepSeek V4.1 Flash; deterministic checks and latency were collected on all successful repeats.
- All requests originated from the same Telnyx stateful actor and called each provider's public API.
- Conversation history contained visible assistant answers only. Hidden reasoning was captured for audit but was not added to later turns.
- `reasoning_effort` was requested as `low` for every candidate. Provider implementations may still differ.
- TTFT is the first non-empty model delta. TTFA is the first non-whitespace visible answer content. E2E ends when the streamed model response completes.
- Failed requests remain reliability failures and are excluded from successful-request latency percentiles. Judge failures are not converted into low candidate scores.
- Observed p95 values describe this sample and are not provider SLAs.
