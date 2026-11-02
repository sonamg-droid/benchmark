# Data

## Request-level files

`raw-measurements.csv` contains all 1,000 exported rows: 24 warm-ups, 16 cache-seed requests and 960 measured requests. `clean-successful-requests.csv` contains only successful rows with visible answer content.

Model output and reasoning text were removed from both public files. Status, timing, stream behavior, token counts, workload, concurrency and cache-mode fields remain unchanged. Provider error bodies were reduced to an error category.

| Column | Meaning |
|---|---|
| `concurrency` | Target simultaneous request count for that cell |
| `cache_mode` | Warm-up, uncached, cache-seed or shared-prefix test phase |
| `ttft_ms` | Time to first model activity, including reasoning |
| `ttfa_ms` | Time to first visible answer content |
| `e2e_ms` | Complete streamed request latency |
| `median_itl_ms` | Median interval between streamed output chunks |
| `effective_tok_s` | Output-token generation rate derived from measured timing |
| `error_category` | Sanitized failure category |

## Summary files

- `summary.csv`: profile/concurrency/cache-mode latency, throughput and cost aggregates.
- `cost_summary.csv`: published-price estimates from measured token counts.
- `failure_summary.csv`: unsuccessful or no-answer rows.
- `validation_summary.json`: row counts, p95 sample sizes, cost basis and exclusions.
