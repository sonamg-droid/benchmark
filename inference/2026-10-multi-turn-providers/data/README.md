# Data

| File | Contents |
|---|---|
| `turns.csv` | One row per model turn with provider, model, prompt, visible answer, timing and tokens |
| `conversations.csv` | One row per attempted conversation with completion, total response time and token totals |
| `judges.csv` | Blind completion decisions, five 1–5 quality dimensions and concise rationales |
| `objective-checks.csv` | Deterministic scenario checks and outcomes |
| `provider_model_summary.csv` | Canonical provider/model aggregates used in the report |
| `quality_by_provider_model_judge.csv` | Judge results by provider and model |
| `category_leaders.csv` | Metric leaders without combining categories into one score |
| `failure_summary.csv` | Failed conversations and sanitized failure types |

TTFT is first model activity and may be reasoning. TTFA is first visible answer content. Conversation response time sums per-turn E2E model time and excludes user pauses.

Failures remain in reliability denominators and are excluded only from successful-request latency percentiles. Hidden reasoning and raw judge response envelopes were removed from the public export.
