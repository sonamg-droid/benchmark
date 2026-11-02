# Telnyx Inference vs Modal Shared benchmark report

## Scope

This report compares Telnyx Inference with Modal Shared Endpoint for `zai-org/GLM-5.3-Flash`. Traffic originated from a Telnyx Stateful Actor and used the same prompts, reasoning effort, output limits, and request schedule for both managed endpoints. Modal Dedicated was excluded.

The exported dataset contains 1,000 rows: 24 warm-ups, 16 cache-seed requests, and 960 measured requests. Of the measured requests, 959/960 completed with visible answer content and 1 did not. Failed and no-answer requests remain in the raw dataset and are excluded from latency percentiles.

## Results

Across the eight uncached profile/concurrency cells, Telnyx had lower p50 E2E latency in 8/8 cells, lower p95 E2E latency in 6/8 cells, and higher p50 output throughput in 8/8 cells. Based on measured tokens and published list rates, Telnyx's estimated uncached token cost was 70.0% lower for this workload. First-answer latency was mixed and should be read separately from completed-response performance.

| Endpoint | Cache mode | Profile | Concurrency | Completed | p95 N | p50 TTFT | p95 TTFT | p50 TTFA | p95 TTFA | p50 E2E | p95 E2E | p50 tok/s | p50 time/output token | Cost / 1K completed | Est. list cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Modal Shared Endpoint | cached | generation_10k_1024 | 1 | 30/30 | 30 | 420.17 ms | 727.85 ms | 468.82 ms | 787.65 ms | 11537.73 ms | 14966.38 ms | 90.82 tok/s | 11.01 ms/token | 6.2012 USD | 0.186035 USD |
| Modal Shared Endpoint | uncached | generation_10k_1024 | 1 | 30/30 | 30 | 595.91 ms | 1185.71 ms | 831.57 ms | 1967.95 ms | 19845.11 ms | 26307.97 ms | 53.16 tok/s | 18.81 ms/token | 6.4450 USD | 0.193349 USD |
| Modal Shared Endpoint | cached | generation_10k_1024 | 10 | 30/30 | 30 | 916.47 ms | 1532.13 ms | 1017.45 ms | 1533.74 ms | 14719.70 ms | 16966.11 ms | 71.97 tok/s | 13.90 ms/token | 6.1888 USD | 0.185664 USD |
| Modal Shared Endpoint | uncached | generation_10k_1024 | 10 | 30/30 | 30 | 1326.46 ms | 1660.32 ms | 1385.97 ms | 1749.67 ms | 17807.79 ms | 23323.47 ms | 61.30 tok/s | 16.32 ms/token | 6.3996 USD | 0.191988 USD |
| Modal Shared Endpoint | cached | long_100k_256 | 1 | 30/30 | 30 | 1169.27 ms | 4221.78 ms | 1346.35 ms | 4277.67 ms | 8157.87 ms | 18570.31 ms | 41.84 tok/s | 23.90 ms/token | 47.6345 USD | 1.429034 USD |
| Modal Shared Endpoint | uncached | long_100k_256 | 1 | 30/30 | 30 | 4012.83 ms | 4625.32 ms | 4155.00 ms | 5928.95 ms | 9896.19 ms | 14534.66 ms | 43.44 tok/s | 23.02 ms/token | 49.9651 USD | 1.498954 USD |
| Modal Shared Endpoint | cached | long_100k_256 | 10 | 30/30 | 30 | 1649.17 ms | 5718.89 ms | 1660.21 ms | 5973.36 ms | 4769.20 ms | 8877.02 ms | 82.89 tok/s | 12.06 ms/token | 47.4694 USD | 1.424083 USD |
| Modal Shared Endpoint | uncached | long_100k_256 | 10 | 30/30 | 30 | 10483.62 ms | 11873.08 ms | 11055.47 ms | 12160.54 ms | 13629.81 ms | 15026.02 ms | 74.40 tok/s | 13.44 ms/token | 49.7841 USD | 1.493522 USD |
| Modal Shared Endpoint | cached | medium_10k_256 | 1 | 30/30 | 30 | 510.50 ms | 842.11 ms | 510.50 ms | 842.11 ms | 2666.44 ms | 3797.33 ms | 120.37 tok/s | 8.31 ms/token | 5.0971 USD | 0.152914 USD |
| Modal Shared Endpoint | uncached | medium_10k_256 | 1 | 30/30 | 30 | 628.96 ms | 1121.70 ms | 628.96 ms | 1121.70 ms | 3673.06 ms | 4825.27 ms | 85.51 tok/s | 11.70 ms/token | 5.3191 USD | 0.159572 USD |
| Modal Shared Endpoint | cached | medium_10k_256 | 10 | 30/30 | 30 | 986.93 ms | 2500.65 ms | 992.89 ms | 2500.65 ms | 4331.62 ms | 6857.12 ms | 77.17 tok/s | 12.96 ms/token | 5.0803 USD | 0.152409 USD |
| Modal Shared Endpoint | uncached | medium_10k_256 | 10 | 30/30 | 30 | 1683.34 ms | 1975.67 ms | 1683.34 ms | 1975.67 ms | 5362.10 ms | 17673.58 ms | 69.49 tok/s | 14.40 ms/token | 5.3018 USD | 0.159055 USD |
| Modal Shared Endpoint | cached | short_1k_256 | 1 | 30/30 | 30 | 366.91 ms | 781.59 ms | 366.91 ms | 781.59 ms | 5185.76 ms | 9350.99 ms | 53.02 tok/s | 18.86 ms/token | 0.8943 USD | 0.026829 USD |
| Modal Shared Endpoint | uncached | short_1k_256 | 1 | 30/30 | 30 | 343.80 ms | 791.04 ms | 343.80 ms | 791.04 ms | 3760.49 ms | 5487.89 ms | 77.16 tok/s | 12.96 ms/token | 0.9146 USD | 0.027439 USD |
| Modal Shared Endpoint | cached | short_1k_256 | 10 | 30/30 | 30 | 435.76 ms | 679.16 ms | 435.76 ms | 679.16 ms | 3318.03 ms | 3824.12 ms | 87.53 tok/s | 11.42 ms/token | 0.8930 USD | 0.026788 USD |
| Modal Shared Endpoint | uncached | short_1k_256 | 10 | 30/30 | 30 | 551.60 ms | 785.54 ms | 551.60 ms | 785.54 ms | 4332.89 ms | 5094.68 ms | 67.78 tok/s | 14.75 ms/token | 0.9128 USD | 0.027385 USD |
| Telnyx Inference | cached | generation_10k_1024 | 1 | 30/30 | 30 | 660.70 ms | 1612.94 ms | 663.03 ms | 1612.94 ms | 8654.05 ms | 12654.50 ms | 132.34 tok/s | 7.56 ms/token | 1.8545 USD | 0.055636 USD |
| Telnyx Inference | uncached | generation_10k_1024 | 1 | 30/30 | 30 | 772.21 ms | 1629.82 ms | 875.30 ms | 1990.47 ms | 8526.84 ms | 11532.28 ms | 131.25 tok/s | 7.62 ms/token | 1.9340 USD | 0.058020 USD |
| Telnyx Inference | cached | generation_10k_1024 | 10 | 30/30 | 30 | 1049.82 ms | 3398.70 ms | 1100.80 ms | 3461.92 ms | 8911.51 ms | 12885.13 ms | 132.60 tok/s | 7.55 ms/token | 1.8585 USD | 0.055754 USD |
| Telnyx Inference | uncached | generation_10k_1024 | 10 | 30/30 | 30 | 1028.08 ms | 3357.21 ms | 1129.62 ms | 3357.21 ms | 8861.05 ms | 18414.88 ms | 128.40 tok/s | 7.79 ms/token | 1.9262 USD | 0.057786 USD |
| Telnyx Inference | cached | long_100k_256 | 1 | 30/30 | 30 | 2707.41 ms | 5885.42 ms | 2731.33 ms | 5885.42 ms | 4565.56 ms | 7538.31 ms | 159.36 tok/s | 6.28 ms/token | 14.2903 USD | 0.428710 USD |
| Telnyx Inference | uncached | long_100k_256 | 1 | 30/30 | 30 | 4091.56 ms | 6529.94 ms | 4128.22 ms | 7292.16 ms | 5997.02 ms | 9832.08 ms | 154.12 tok/s | 6.49 ms/token | 14.9895 USD | 0.449686 USD |
| Telnyx Inference | cached | long_100k_256 | 10 | 30/30 | 30 | 4056.30 ms | 7354.72 ms | 4095.61 ms | 7470.14 ms | 5953.87 ms | 9089.78 ms | 128.38 tok/s | 7.80 ms/token | 14.2408 USD | 0.427225 USD |
| Telnyx Inference | uncached | long_100k_256 | 10 | 30/30 | 30 | 4538.42 ms | 10633.67 ms | 4538.42 ms | 10633.67 ms | 6207.72 ms | 14065.37 ms | 141.36 tok/s | 7.08 ms/token | 14.9351 USD | 0.448052 USD |
| Telnyx Inference | cached | medium_10k_256 | 1 | 30/30 | 30 | 661.53 ms | 3034.36 ms | 720.84 ms | 3056.25 ms | 2758.81 ms | 8594.68 ms | 140.61 tok/s | 7.11 ms/token | 1.5291 USD | 0.045874 USD |
| Telnyx Inference | uncached | medium_10k_256 | 1 | 30/30 | 30 | 843.87 ms | 3286.69 ms | 843.87 ms | 3286.69 ms | 3071.86 ms | 5725.44 ms | 138.66 tok/s | 7.21 ms/token | 1.5957 USD | 0.047872 USD |
| Telnyx Inference | cached | medium_10k_256 | 10 | 30/30 | 30 | 1080.00 ms | 1837.25 ms | 1080.00 ms | 1837.25 ms | 2899.36 ms | 4148.05 ms | 140.91 tok/s | 7.10 ms/token | 1.5241 USD | 0.045723 USD |
| Telnyx Inference | uncached | medium_10k_256 | 10 | 30/30 | 30 | 912.92 ms | 2569.58 ms | 912.92 ms | 2569.58 ms | 2657.64 ms | 4554.72 ms | 150.54 tok/s | 6.64 ms/token | 1.5905 USD | 0.047716 USD |
| Telnyx Inference | cached | short_1k_256 | 1 | 29/30 | 29 | 496.49 ms | 2034.37 ms | 496.49 ms | 2034.37 ms | 2334.39 ms | 3984.47 ms | 145.46 tok/s | 6.87 ms/token | 0.2683 USD | 0.007780 USD |
| Telnyx Inference | uncached | short_1k_256 | 1 | 30/30 | 30 | 351.73 ms | 1159.58 ms | 351.73 ms | 1159.58 ms | 2315.25 ms | 4024.05 ms | 156.54 tok/s | 6.39 ms/token | 0.2744 USD | 0.008232 USD |
| Telnyx Inference | cached | short_1k_256 | 10 | 30/30 | 30 | 412.33 ms | 2799.23 ms | 412.33 ms | 2799.23 ms | 2247.42 ms | 5199.97 ms | 143.65 tok/s | 6.96 ms/token | 0.2679 USD | 0.008037 USD |
| Telnyx Inference | uncached | short_1k_256 | 10 | 30/30 | 30 | 537.55 ms | 988.26 ms | 537.55 ms | 988.26 ms | 2634.61 ms | 7297.82 ms | 119.91 tok/s | 8.34 ms/token | 0.2739 USD | 0.008216 USD |

## Interpretation guardrails

- TTFT is time to first model activity, including reasoning. TTFA is time to first visible answer text.
- Time per output token is derived from generation time after TTFA divided by generated output tokens. It is a cross-provider inter-token-latency proxy, not direct observation of each tokenizer emission.
- A lower latency value is better; higher throughput and reliability are better.
- Cost is estimated from measured token counts and the snapshotted published list prices. It is not a provider invoice or billing reconciliation.
- Rate-limit responses are shown as reliability and limit findings, not silently treated as model latency.
- The APIs reported cached-token evidence for 0 requests. Because that count is zero, cached-mode latency is shown as an experimental condition, but no cache hit or discounted cached-input cost is claimed.
- Each p95 value is interpolated from the completed requests in that cell; the `p95 N` column shows the sample size.
