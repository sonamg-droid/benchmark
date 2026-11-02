# Multi-turn task completion benchmark v1

This report keeps completion, quality, reliability, latency, and token usage separate. It does not calculate a composite winner.

## Run scope

- Dataset: `multi-turn-task-completion-v1`
- Candidate models: 3
- Scenarios: 15
- Conversation attempts: 45
- Blind judges: DeepSeek V4.1 Flash, MiniMax M3

## Completion, reliability, and tokens

| Model | Completed | Objective checks | Judge completion | Mean input tokens | Mean output tokens |
| --- | --- | --- | --- | --- | --- |
| GLM 5.3 | 15/15 (100.0%) | 23/28 (82.1%) | 27/30 (90.0%) | 3399 | 2151 |
| GLM 5.3 Flash | 15/15 (100.0%) | 22/28 (78.6%) | 27/30 (90.0%) | 2919 | 1886 |
| Kimi K3 | 15/15 (100.0%) | 23/28 (82.1%) | 30/30 (100.0%) | 3319 | 1864 |

## Blind quality scores

Scores use a 1-5 rubric. Results are shown per judge rather than silently averaged across judges.

| Model | Judge | N | Task completion | Correctness | State tracking | Corrections | Usability |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GLM 5.3 | DeepSeek V4.1 Flash | 15 | 4.80 | 4.87 | 4.80 | 4.87 | 4.87 |
| GLM 5.3 | MiniMax M3 | 15 | 4.60 | 4.73 | 4.80 | 4.87 | 4.73 |
| GLM 5.3 Flash | DeepSeek V4.1 Flash | 15 | 4.80 | 4.80 | 4.80 | 4.87 | 4.87 |
| GLM 5.3 Flash | MiniMax M3 | 15 | 4.67 | 4.80 | 4.73 | 4.93 | 4.67 |
| Kimi K3 | DeepSeek V4.1 Flash | 15 | 4.93 | 4.87 | 4.87 | 5.00 | 5.00 |
| Kimi K3 | MiniMax M3 | 15 | 4.73 | 4.93 | 4.93 | 5.00 | 4.80 |

## Per-turn latency

| Model | Successful turns | p50 TTFT | p95 TTFT | p50 TTFA | p95 TTFA | p50 E2E | p95 E2E |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GLM 5.3 | 60 | 0.41s | 1.97s | 0.52s | 2.86s | 3.08s | 15.81s |
| GLM 5.3 Flash | 60 | 0.33s | 2.20s | 0.41s | 2.60s | 2.03s | 8.60s |
| Kimi K3 | 60 | 0.38s | 0.95s | 0.49s | 2.20s | 2.51s | 15.59s |

## Total conversation response time

| Model | p50 total response time | p95 total response time |
| --- | --- | --- |
| GLM 5.3 | 16.38s | 53.19s |
| GLM 5.3 Flash | 8.35s | 31.27s |
| Kimi K3 | 9.36s | 55.71s |

## Judge agreement

- Completion decision agreement: 43/45 (95.6%)
- Mean absolute difference across the five rubric scores: 0.16 points
- Review individual conversations when the judges disagree on completion or differ materially on scores.

## Measurement notes

- TTFT is the first non-empty model delta and may be reasoning.
- TTFA is the first non-whitespace visible answer content.
- E2E is measured per model turn. Total response time is the sum of successful model-turn E2E values within a conversation.
- Failed model requests are counted as reliability failures and excluded from successful-turn latency percentiles.
- Judge failures remain visible and are not converted into low candidate scores.
