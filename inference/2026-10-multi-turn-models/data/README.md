# Data

| File | Contents |
|---|---|
| `turns.csv` | One row per model turn: prompt, visible answer, TTFT, TTFA, E2E and token usage |
| `conversations.csv` | Conversation-level completion, total response time, tokens and check totals |
| `judges.csv` | Blind judge completion decisions, five 1–5 rubric scores and concise rationales |
| `objective-checks.csv` | Deterministic requirement checks for every conversation |
| `model_summary.csv` | Model-level completion, checks, token and conversation-latency aggregates |
| `latency_summary.csv` | Per-model p50 and observed p95 TTFT, TTFA and E2E |
| `quality_by_judge.csv` | Quality dimensions kept separate by judge |
| `judge_agreement.csv` | Completion agreement and score differences between judges |

TTFT is first model activity and may contain reasoning. TTFA is first visible answer content. E2E is one complete model turn. Conversation response time sums E2E across the fixed turns and excludes user pauses.

Hidden reasoning text and raw judge response envelopes were removed from the public export. No measured rows were removed.
