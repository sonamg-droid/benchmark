# Data

## `measurements.csv`

One row per provider and prompt variant. It preserves status, timing, streamed-output type, token counts and throughput fields. Provider error bodies are reduced to an error category so request identifiers and account-specific links are not published.

Headline timing fields are measured in milliseconds:

| Column | Meaning |
|---|---|
| `ttft_ms` | Time to first non-empty model activity, which may be reasoning |
| `ttfa_ms` | Time to first visible answer content |
| `e2e_ms` | Time from request send through stream completion |
| `median_itl_ms` | Median interval between streamed output chunks |
| `effective_tok_s` | Provider-reported output tokens divided by measured generation time |
| `prompt_tokens`, `output_tokens` | Provider-reported token usage where available |
| `error_category` | Sanitized failure category; empty for successful rows |

## `first-delta-diagnostic.csv`

Small diagnostic capture used to identify whether the first streamed activity was reasoning or visible content. Literal reasoning text is intentionally omitted.

## `summary.json`

Machine-readable aggregates used to generate the report tables and charts.
