# GLM 5.3 fresh-prompt latency, September 2026

Part of the [inference benchmarks](../README.md). This run compared `zai-org/GLM-5.3` on Telnyx, Baseten, Together AI and Fireworks using 60 distinct prompts across six input/output profiles.

| Result | Observation |
|---|---|
| Completed responses | 230 of 240 attempts |
| Lowest median completed-response latency | Telnyx in 5 of 6 profiles |
| Lowest median time to first visible answer | Together AI in 4 of 6 profiles; Telnyx in 2 |
| Largest profile | About 88.7K input tokens and 1,200 output tokens |

The prompts were varied from the beginning to reduce exact-prefix reuse. This was not a controlled cache experiment, and differences from earlier repeated-prompt measurements cannot be attributed to caching alone.

Read [`report/REPORT.md`](report/REPORT.md) for the complete tables, methodology and limitations. The public article is [GLM-5.3 latency benchmarks across four inference providers](https://telnyx.com/resources/glm-5-3-latency-benchmarks-provider).

## Layout

| Path | What it is |
|---|---|
| `report/` | Full report and charts |
| `data/measurements.csv` | One row per attempted provider/prompt pair, without model reasoning text |
| `data/first-delta-diagnostic.csv` | Small diagnostic distinguishing first model activity from first visible answer |
| `config/` | Prompt fixtures plus the deterministic prompt-variant manifest |
| `scripts/` | Actor orchestration and export scripts used for the run |

## Read before quoting

- Requests ran sequentially, not as a concurrency or capacity test.
- Provider order was not rotated, so time-varying load is a possible confounder.
- Ten incomplete or failed requests remain in the data but are excluded from latency percentiles. Several were account-credit failures and should not be interpreted as provider reliability.
- TTFT can include reasoning. TTFA is the first visible answer content.
- Observed p95 values describe this sample and are not SLAs.

## Disclosure

Run by Telnyx staff from a Telnyx Stateful Actor on September 17, 2026. Telnyx Inference was one of the four compared providers. The actor was the common request origin; that does not establish which data center served any provider request.
